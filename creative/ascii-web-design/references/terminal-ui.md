# 伪终端站范式（整站 CLI 作品集）

把整站做成一个 Web 终端：用户输命令浏览内容（`help / ls / about / projects`），开屏 FIGlet banner + neofetch 风字符画。参考实现：CLIWebsite（命令导航 + 贪吃蛇 + ASCII 时钟）、xscript.net（fake-terminal 自动打字）、getascii.com（Astro 纯静态 CRT 工具站）。

```html
<!-- 骨架：<pre> 输出区 + 单行输入。命令表驱动，易扩展 -->
<pre id="term">  _____ ____  ____
 / ___/|    \|    \    WELCOME
(   \_ |  o  )  o  )   type "help"
 \__  ||   _/|   _/
 |  \ ||  |  |  |
  \__)|__|  |__|
</pre>
<div class="input-line">
  <span class="prompt">visitor@site:~$ </span>
  <input id="cmd" autofocus autocomplete="off" spellcheck="false">
</div>
<script>
// 输出卫生：剥离控制字符（防 ANSI 注入），仅保留 \t 与 \n
const sanitize = s => String(s).replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '');

const COMMANDS = {
  help:  () => "commands: " + Object.keys(COMMANDS).join('  '),
  about: () => "…",           // 内容即数据：每页一条命令
  projects: () => "…",
  clear: () => { term.textContent = ''; return ''; },
};
const history = []; let hi = 0, draft = '';
cmd.onkeydown = e => {
  if (e.key === 'Enter') {
    const t = sanitize(cmd.value.trim());
    term.textContent += `\nvisitor@site:~$ ${t}\n`;
    const fn = COMMANDS[t];
    const out = fn ? fn() : `${t}: command not found`;
    if (out) term.textContent += sanitize(out) + '\n';
    if (t) { history.push(t); }
    hi = history.length; cmd.value = '';
    term.scrollTop = term.scrollHeight;
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (hi === history.length) draft = cmd.value;  // 首次↑前保存草稿
    if (hi > 0) cmd.value = history[--hi];
  }
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (hi < history.length) cmd.value = history[++hi];
    if (hi === history.length) cmd.value = draft;  // 越过后恢复草稿
  }
  if (e.key === 'Tab') {                           // 补全：唯一前缀匹配
    e.preventDefault();
    const p = cmd.value;
    const hit = Object.keys(COMMANDS).filter(c => c.startsWith(p));
    if (hit.length === 1) cmd.value = hit[0];
    else if (hit.length > 1) term.textContent += '\n' + hit.join('  ') + '\n';
  }
};
</script>
```

要点：
- **命令表 = 纯数据对象**，新增页面 = 新增键，命令自动出现在 `help`。
- **↑↓ 历史命令、Tab 补全**是"像真终端"的及格线；登录态/密码页做 easter egg（CLIWebsite 的 `secret` 页）。
- **打字机输出**：长文本按字符/按行延迟输出（30–50ms/行），配光标闪烁 `▊`——机器感来自节奏，不是音效。
- **fake 自动模式**（录屏/直播场景）：无需输入，脚本化逐条"敲"命令并输出，xscript.net 即此形态。
- 移动端：软键盘体验差，给命令加可点按的快捷按钮行。
- 命令别名（`ls`≡`dir`）和 `man <cmd>` 帮助页是加分项。

