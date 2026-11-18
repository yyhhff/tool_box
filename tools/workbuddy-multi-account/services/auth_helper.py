"""
WorkBuddy 加密凭据解密助手

原理（移植自 github.com/88lin/workbuddy-auto-signin，MIT License, Copyright (c) 2026 88lin）：
- 桌面端落盘的 accessToken 是 {$wbEncrypted: 1, envelope: base64(...)} 信封
- envelope.suite=1（sym-v1）：AES-256-GCM，密钥 = sha256(客户端原生存储的 atRestSecretKey)
- 密钥只能通过 WorkBuddy.exe 的原生绑定模块 electron_browser_workbuddy_storage 读取
- 因此以 ELECTRON_RUN_AS_NODE=1 用 WorkBuddy.exe 执行内嵌 JS，stdin 送密文、stdout 收明文
- 明文 token 仅存在于本进程内存，不落盘；快照文件始终保留密文原样
"""
import json
import os
import re
import subprocess
import threading
import time
from contextlib import closing

# ---- 常量（与官方脚本一致） ----

AUTH_HELPER_TIMEOUT = 10.0
AUTH_INPUT_LIMIT = 65536
AUTH_OUTPUT_LIMIT = 65536
TOKEN_LIMIT = 32768
TOKEN_RE = re.compile(r"[A-Za-z0-9._~+/-]+=*")

AUTH_REASONS = {
    "INVALID_FORMAT": "登录凭据格式无效，请检查凭据来源和客户端版本",
    "UNSUPPORTED_ENVELOPE": "尚不支持此加密凭据格式，请更新工具；重新登录不会改变加密格式",
    "RUNTIME_NOT_FOUND": "未找到 WorkBuddy 客户端，请用 WORKBUDDY_EXE 环境变量指定其可执行文件",
    "INVALID_RUNTIME_PATH": "WORKBUDDY_EXE 不是可用的可执行文件，请核对路径",
    "RUNTIME_UNAVAILABLE": "客户端运行时不支持所需的原生存储接口，请检查客户端和工具版本",
    "KEY_MISMATCH": "凭据与所选客户端的密钥不匹配，请用 WORKBUDDY_EXE 指定对应客户端",
    "DECRYPT_FAILED": "加密凭据认证失败，请检查客户端版本及凭据是否完整",
    "HELPER_TIMEOUT": "凭据处理超时，已停止子进程，请稍后重试",
    "HELPER_PROTOCOL": "客户端凭据助手返回无效结果，请检查客户端和工具版本",
}

# 固定代码只走 argv；加密字段走 stdin。密钥材料不离开该子进程。仅支持 sym-v1 / suite 1。
AUTH_HELPER_JS = r"""
'use strict';
const crypto = require('crypto');
const inputLimit = 65536;
const failure = reason => { throw {reason}; };
const object = x => x !== null && typeof x === 'object' && !Array.isArray(x);
function base64(value, length) {
  if (typeof value !== 'string' || value.length > inputLimit) failure('INVALID_FORMAT');
  const bytes = Buffer.from(value, 'base64');
  if (bytes.toString('base64') !== value || (length !== undefined && bytes.length !== length))
    failure('INVALID_FORMAT');
  return bytes;
}
function utf8(bytes) {
  const text = bytes.toString('utf8');
  if (!Buffer.from(text, 'utf8').equals(bytes)) failure('INVALID_FORMAT');
  return text;
}
function decode(value) {
  if (!object(value) || Object.keys(value).sort().join(',') !== '$wbEncrypted,envelope' || value.$wbEncrypted !== 1)
    failure('UNSUPPORTED_ENVELOPE');
  let envelope;
  try { envelope = JSON.parse(utf8(base64(value.envelope))); }
  catch (e) { failure(e.reason || 'INVALID_FORMAT'); }
  if (!object(envelope) || !Number.isInteger(envelope.suite)) failure('INVALID_FORMAT');
  if (envelope.suite !== 1) failure('UNSUPPORTED_ENVELOPE');
  if (Object.keys(envelope).sort().join(',') !== 'authTag,ciphertext,keyId,nonce,suite' ||
      typeof envelope.keyId !== 'string' || !/^[0-9a-f]{16}$/.test(envelope.keyId)) failure('INVALID_FORMAT');
  return {keyId: envelope.keyId, nonce: base64(envelope.nonce, 12),
    tag: base64(envelope.authTag, 16), ciphertext: base64(envelope.ciphertext)};
}
function nativeStorage() {
  try {
    const storage = process._linkedBinding('electron_browser_workbuddy_storage');
    if (typeof storage.loggerGet !== 'function') failure('RUNTIME_UNAVAILABLE');
    return storage;
  } catch (_) { failure('RUNTIME_UNAVAILABLE'); }
}
function decrypt(envelope) {
  let payload;
  try { payload = JSON.parse(nativeStorage().loggerGet()); }
  catch (_) { failure('RUNTIME_UNAVAILABLE'); }
  let key;
  let plaintext;
  try {
    if (!object(payload) || payload.version !== 1) failure('RUNTIME_UNAVAILABLE');
    let secret;
    try { secret = base64(payload.atRestSecretKey, 32); }
    catch (_) { failure('RUNTIME_UNAVAILABLE'); }
    const empty = secret.every(b => b === 0);
    secret.fill(0);
    if (empty) failure('RUNTIME_UNAVAILABLE');
    key = crypto.createHash('sha256').update(payload.atRestSecretKey, 'utf8').digest();
    payload = null;
    if (crypto.createHash('sha256').update(key).digest('hex').slice(0, 16) !== envelope.keyId)
      failure('KEY_MISMATCH');
    const lp = s => {
      const bytes = Buffer.from(s, 'utf8');
      const length = Buffer.alloc(4); length.writeUInt32BE(bytes.length);
      return Buffer.concat([length, bytes]);
    };
    const aad = Buffer.concat([Buffer.from('WB-AAD\0', 'ascii'), Buffer.from([1]),
      lp('WBEV1'), lp('sym-v1'), Buffer.from([0, 0, 0, 1]), lp(envelope.keyId), Buffer.from([2, 0, 0])]);
    try {
      const cipher = crypto.createDecipheriv('aes-256-gcm', key, envelope.nonce, {authTagLength: 16});
      cipher.setAAD(aad); cipher.setAuthTag(envelope.tag);
      plaintext = Buffer.concat([cipher.update(envelope.ciphertext), cipher.final()]);
    } catch (_) { failure('DECRYPT_FAILED'); }
    const token = utf8(plaintext);
    if (!token.length || token.length > 32768 || !/^[A-Za-z0-9._~+\/-]+=*$/.test(token))
      failure('INVALID_FORMAT');
    return token;
  } finally {
    if (key) key.fill(0);
    if (plaintext) plaintext.fill(0);
  }
}
let chunks = [], size = 0;
function reply(value) {
  process.stdout.write(JSON.stringify({version: 1, ...value}), () => process.exit(value.ok ? 0 : 1));
}
process.stdin.on('data', chunk => {
  size += chunk.length;
  if (size > inputLimit) reply({ok: false, reason: 'INVALID_FORMAT'});
  else chunks.push(chunk);
});
process.stdin.on('error', () => reply({ok: false, reason: 'HELPER_PROTOCOL'}));
process.stdin.on('end', () => {
  try {
    const request = JSON.parse(utf8(Buffer.concat(chunks))); chunks = [];
    if (!object(request) || request.version !== 1) failure('HELPER_PROTOCOL');
    if (request.operation === 'probe') {
      nativeStorage();
      if (!crypto.getCiphers().includes('aes-256-gcm')) failure('RUNTIME_UNAVAILABLE');
      reply({ok: true, electron: process.versions.electron || 'unknown'});
    } else if (request.operation === 'decrypt') {
      reply({ok: true, accessToken: decrypt(decode(request.value))});
    } else failure('HELPER_PROTOCOL');
  } catch (e) {
    const reasons = ['INVALID_FORMAT','UNSUPPORTED_ENVELOPE','RUNTIME_UNAVAILABLE',
      'KEY_MISMATCH','DECRYPT_FAILED','HELPER_PROTOCOL'];
    reply({ok: false, reason: reasons.includes(e.reason) ? e.reason : 'HELPER_PROTOCOL'});
  }
});
"""


class AuthHelperError(Exception):
    """只携带固定的非敏感原因，不携带任何凭据内容"""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(AUTH_REASONS.get(reason, "本地未找到有效登录会话，请先登录客户端"))


def find_runtime() -> str:
    """定位 WorkBuddy.exe：环境变量 > 常规安装位 > 本机实际安装位 > 注册表卸载项。"""
    override = os.environ.get("WORKBUDDY_EXE")
    if override:
        path = os.path.abspath(os.path.expanduser(override))
        if not os.path.isfile(path):
            raise AuthHelperError("INVALID_RUNTIME_PATH")
        return path
    home = os.path.expanduser("~")
    local = os.environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
    candidates = [
        os.path.join(local, "Programs", "WorkBuddy", "WorkBuddy.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), "WorkBuddy", "WorkBuddy.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "WorkBuddy", "WorkBuddy.exe"),
        os.path.join("G:\\", "WorkBuddy", "WorkBuddy.exe"),  # 本机实际安装位
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return os.path.abspath(path)
    registered = _registry_runtime()
    if registered:
        return registered
    raise AuthHelperError("RUNTIME_NOT_FOUND")


def _registry_runtime():
    """从注册表卸载项找 WorkBuddy.exe（只读字符串值，不解释卸载命令）。"""
    if os.name != "nt":
        return None
    try:
        import winreg
    except ImportError:
        return None
    subkey = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ | view) as root:
                    for index in range(winreg.QueryInfoKey(root)[0]):
                        try:
                            with winreg.OpenKey(root, winreg.EnumKey(root, index),
                                                0, winreg.KEY_READ | view) as entry:
                                name, _ = winreg.QueryValueEx(entry, "DisplayName")
                                if not isinstance(name, str) or \
                                        not re.fullmatch(r"WorkBuddy\S*", name.strip(), re.IGNORECASE):
                                    continue
                                for field in ("InstallLocation", "DisplayIcon"):
                                    try:
                                        value, _ = winreg.QueryValueEx(entry, field)
                                    except OSError:
                                        continue
                                    if not isinstance(value, str):
                                        continue
                                    value = value.strip().strip('"').split(",")[0].strip()
                                    candidate = os.path.join(value, "WorkBuddy.exe")
                                    if os.path.isfile(candidate):
                                        return candidate
                        except OSError:
                            continue
            except OSError:
                continue
    return None


def decrypt_token(value) -> str:
    """解密 {$wbEncrypted, envelope} 信封，返回明文 token（仅内存）。

    value 接受两种形态：凭据文件中的加密对象（dict），或 base64 envelope 字符串。
    通过 WorkBuddy.exe（ELECTRON_RUN_AS_NODE=1）执行 AUTH_HELPER_JS 完成。
    """
    if isinstance(value, dict):
        payload = value
    elif isinstance(value, str) and value:
        payload = value
    else:
        raise AuthHelperError("INVALID_FORMAT")
    if len(json.dumps(payload, ensure_ascii=True)) > AUTH_INPUT_LIMIT:
        raise AuthHelperError("INVALID_FORMAT")
    exe = find_runtime()
    data = json.dumps({"operation": "decrypt", "value": value, "version": 1},
                      ensure_ascii=True).encode("ascii")
    if len(data) > AUTH_INPUT_LIMIT:
        raise AuthHelperError("INVALID_FORMAT")

    # 剥离可能干扰 Electron/Node 运行时的环境变量（与官方脚本一致）
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith(("NODE_", "ELECTRON_", "WORKBUDDY_"))}
    env["ELECTRON_RUN_AS_NODE"] = "1"
    try:
        process = subprocess.Popen([exe, "-e", AUTH_HELPER_JS], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env=env, shell=False,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError:
        raise AuthHelperError("RUNTIME_UNAVAILABLE") from None

    output = {}
    failed = threading.Event()

    def read_pipe(name, pipe, limit):
        try:
            captured = pipe.read(limit + 1)
            if len(captured) > limit:
                failed.set()
                process.kill()
            else:
                output[name] = captured
        except OSError:
            failed.set()

    def write_pipe():
        try:
            process.stdin.write(data)
            process.stdin.close()
        except OSError:
            failed.set()

    workers = [threading.Thread(target=read_pipe, args=("stdout", process.stdout, AUTH_OUTPUT_LIMIT), daemon=True),
               threading.Thread(target=read_pipe, args=("stderr", process.stderr, 8192), daemon=True),
               threading.Thread(target=write_pipe, daemon=True)]
    deadline = time.monotonic() + AUTH_HELPER_TIMEOUT
    try:
        for worker in workers:
            worker.start()
        try:
            process.wait(timeout=max(0.001, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            raise AuthHelperError("HELPER_TIMEOUT") from None
        for worker in workers:
            worker.join(max(0, deadline - time.monotonic()))
        if any(worker.is_alive() for worker in workers):
            raise AuthHelperError("HELPER_TIMEOUT")
        if failed.is_set():
            raise AuthHelperError("HELPER_PROTOCOL")
        try:
            reply = json.loads(output.get("stdout", b"").decode("utf-8"))
        except (ValueError, UnicodeError):
            raise AuthHelperError("HELPER_PROTOCOL") from None
        if not isinstance(reply, dict) or reply.get("version") != 1:
            raise AuthHelperError("HELPER_PROTOCOL")
        if reply.get("ok") is False and process.returncode == 1:
            reason = reply.get("reason")
            raise AuthHelperError(reason if reason in AUTH_REASONS else "HELPER_PROTOCOL")
        if reply.get("ok") is not True or process.returncode != 0:
            raise AuthHelperError("HELPER_PROTOCOL")
        token = reply.get("accessToken")
        if not isinstance(token, str) or not token or len(token) > TOKEN_LIMIT \
                or TOKEN_RE.fullmatch(token) is None:
            raise AuthHelperError("HELPER_PROTOCOL")
        return token
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        for worker in workers:
            if worker.ident is not None:
                worker.join(1)
        if not any(worker.is_alive() for worker in workers):
            for pipe in (process.stdin, process.stdout, process.stderr):
                pipe.close()


def probe() -> str:
    """探测运行时解密能力，返回 electron 版本（诊断用）。"""
    exe = find_runtime()
    data = json.dumps({"operation": "probe", "version": 1}, ensure_ascii=True).encode("ascii")
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith(("NODE_", "ELECTRON_", "WORKBUDDY_"))}
    env["ELECTRON_RUN_AS_NODE"] = "1"
    process = subprocess.Popen([exe, "-e", AUTH_HELPER_JS], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               env=env, shell=False,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        out, _err = process.communicate(data, timeout=AUTH_HELPER_TIMEOUT)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        raise AuthHelperError("HELPER_TIMEOUT") from None
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    if process.returncode != 0:
        try:
            reason = json.loads(out.decode("utf-8")).get("reason", "HELPER_PROTOCOL")
        except (ValueError, UnicodeError):
            reason = "HELPER_PROTOCOL"
        raise AuthHelperError(reason if reason in AUTH_REASONS else "HELPER_PROTOCOL")
    try:
        reply = json.loads(out.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise AuthHelperError("HELPER_PROTOCOL") from None
    if reply.get("ok") is not True:
        raise AuthHelperError(reply.get("reason", "HELPER_PROTOCOL")
                              if reply.get("reason") in AUTH_REASONS else "HELPER_PROTOCOL")
    return reply.get("electron", "unknown")
