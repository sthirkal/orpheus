#!/usr/bin/env python3
"""
orpheus — terminal note editor
  orpheus              new note
  orpheus myfile.md    open file

keybinds (nano-style):
  ctrl+o   save
  ctrl+x   quit
  ctrl+r   open file
  ctrl+k   cut line
  ctrl+u   paste line
  ctrl+w   find
  ctrl+z   undo
  ctrl+g   go to line
  ctrl+l   jump to end
  ctrl+a   jump to start
"""

import curses, sys, os, time

class Orpheus:
    def __init__(self, stdscr, filename=None):
        self.stdscr    = stdscr
        self.filename  = filename
        self.lines     = [""]
        self.cx = self.cy = 0
        self.sx = self.sy = 0
        self.modified  = False
        self.msg       = ""
        self.msg_time  = 0
        self.undo      = []
        self.clipboard = ""
        self.find_term = ""

        curses.start_color()
        curses.use_default_colors()
        self._colors()
        curses.curs_set(1)
        stdscr.keypad(True)
        stdscr.timeout(-1)

        if filename and os.path.exists(filename):
            self._load(filename)
        elif filename:
            self._set_msg(f"new file: {filename}")

    def _colors(self):
        try:
            curses.init_color(8, 1000, 720, 770)
            PINK = 8
        except Exception:
            PINK = curses.COLOR_MAGENTA
        B = curses.COLOR_BLACK
        W = curses.COLOR_WHITE
        curses.init_pair(1, W,    B)
        curses.init_pair(2, PINK, B)
        curses.init_pair(3, W,    B)
        curses.init_pair(4, W,    B)
        curses.init_pair(5, B,    PINK)

    @property
    def H(self): return curses.LINES
    @property
    def W(self): return curses.COLS
    @property
    def ETOP(self): return 1
    @property
    def EBOT(self): return self.H - 2
    @property
    def EH(self):   return max(1, self.EBOT - self.ETOP)
    @property
    def GUTTER(self): return 4
    @property
    def EW(self):   return max(1, self.W - self.GUTTER)

    def _w(self, y, x, text, attr=0):
        if y < 0 or y >= self.H or x < 0 or x >= self.W - 1:
            return
        avail = self.W - x - 1
        if avail <= 0:
            return
        try:
            self.stdscr.addstr(y, x, text[:avail], attr)
        except curses.error:
            pass

    def _wfill(self, y, text, attr=0):
        w = max(0, self.W - 1)
        s = (text + " " * w)[:w]
        try:
            self.stdscr.addstr(y, 0, s, attr)
        except curses.error:
            pass

    def _load(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                self.lines = f.read().split("\n")
            if not self.lines:
                self.lines = [""]
            self.modified = False
            self.filename = path
            self._set_msg(f"opened: {path}")
        except Exception as e:
            self._set_msg(f"error: {e}")

    def _save(self):
        if not self.filename:
            name = self._prompt("file name to write: ")
            if name is None:
                return
            self.filename = name.strip() or "note.md"
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                f.write("\n".join(self.lines))
            self.modified = False
            self._set_msg(f"saved: {self.filename}")
        except Exception as e:
            self._set_msg(f"save error: {e}")

    def _open_file(self):
        name = self._prompt("file to open: ")
        if name is None:
            return
        name = name.strip()
        if not name:
            return
        if self.modified:
            ans = self._prompt("unsaved changes — discard? (y/n): ")
            if not (ans and ans.strip().lower() == "y"):
                return
        if os.path.exists(name):
            self._load(name)
        else:
            self._set_msg(f"not found: {name}")
        self.cx = self.cy = self.sx = self.sy = 0

    def _push(self):
        self.undo.append((list(self.lines), self.cy, self.cx))
        if len(self.undo) > 500:
            self.undo.pop(0)

    def _undo(self):
        if self.undo:
            self.lines, self.cy, self.cx = self.undo.pop()
            self.modified = True
            self._set_msg("undo")
        else:
            self._set_msg("nothing to undo")

    def _cut(self):
        self._push()
        self.clipboard = self.lines[self.cy]
        self.lines.pop(self.cy)
        if not self.lines:
            self.lines = [""]
        self.cy = min(self.cy, len(self.lines) - 1)
        self.cx = 0
        self.modified = True
        self._set_msg("line cut")

    def _paste(self):
        self._push()
        self.lines.insert(self.cy, self.clipboard)
        self.cy = min(self.cy + 1, len(self.lines) - 1)
        self.cx = 0
        self.modified = True

    def _find(self):
        term = self._prompt("search: ", self.find_term)
        if term is None:
            return
        term = term.strip()
        if not term:
            return
        self.find_term = term
        for i in range(1, len(self.lines) + 1):
            y = (self.cy + i) % len(self.lines)
            x = self.lines[y].find(term)
            if x != -1:
                self.cy, self.cx = y, x
                self._set_msg(f"found at line {y + 1}")
                return
        self._set_msg(f"not found: {term}")

    def _goto(self):
        s = self._prompt("go to line: ")
        if s and s.strip().isdigit():
            n = max(1, min(int(s.strip()), len(self.lines)))
            self.cy, self.cx = n - 1, 0
            self._set_msg(f"line {n}")

    def _set_msg(self, text):
        self.msg      = text
        self.msg_time = time.time()

    def _prompt(self, label, prefill=""):
        buf  = list(prefill)
        pos  = len(buf)
        attr = curses.color_pair(5)
        while True:
            text = label + "".join(buf)
            self._wfill(self.H - 2, text, attr)
            cx = min(len(label) + pos, self.W - 2)
            try:
                self.stdscr.move(self.H - 2, cx)
            except curses.error:
                pass
            self.stdscr.refresh()
            ch = self.stdscr.getch()
            if ch in (10, 13):
                return "".join(buf)
            elif ch in (27, 7):
                return None
            elif ch in (curses.KEY_BACKSPACE, 127, 8):
                if pos > 0:
                    buf.pop(pos - 1)
                    pos -= 1
            elif ch == curses.KEY_DC:
                if pos < len(buf):
                    buf.pop(pos)
            elif ch == curses.KEY_LEFT:
                pos = max(0, pos - 1)
            elif ch == curses.KEY_RIGHT:
                pos = min(len(buf), pos + 1)
            elif ch == curses.KEY_HOME:
                pos = 0
            elif ch == curses.KEY_END:
                pos = len(buf)
            elif 32 <= ch <= 126:
                buf.insert(pos, chr(ch))
                pos += 1

    def _clamp(self):
        self.cy = max(0, min(self.cy, len(self.lines) - 1))
        self.cx = max(0, min(self.cx, len(self.lines[self.cy])))

    def _scroll(self):
        self._clamp()
        if self.cy < self.sy:
            self.sy = self.cy
        elif self.cy >= self.sy + self.EH:
            self.sy = self.cy - self.EH + 1
        if self.cx < self.sx:
            self.sx = self.cx
        elif self.cx >= self.sx + self.EW:
            self.sx = self.cx - self.EW + 1

    def _ins(self, ch):
        self._push()
        ln = self.lines[self.cy]
        self.lines[self.cy] = ln[:self.cx] + ch + ln[self.cx:]
        self.cx += 1
        self.modified = True

    def _enter(self):
        self._push()
        ln = self.lines[self.cy]
        self.lines[self.cy] = ln[:self.cx]
        self.lines.insert(self.cy + 1, ln[self.cx:])
        self.cy += 1
        self.cx = 0
        self.modified = True

    def _bs(self):
        if self.cx > 0:
            self._push()
            ln = self.lines[self.cy]
            self.lines[self.cy] = ln[:self.cx - 1] + ln[self.cx:]
            self.cx -= 1
            self.modified = True
        elif self.cy > 0:
            self._push()
            prev = self.lines[self.cy - 1]
            cur  = self.lines.pop(self.cy)
            self.cy -= 1
            self.cx = len(prev)
            self.lines[self.cy] = prev + cur
            self.modified = True

    def _del(self):
        ln = self.lines[self.cy]
        if self.cx < len(ln):
            self._push()
            self.lines[self.cy] = ln[:self.cx] + ln[self.cx + 1:]
            self.modified = True
        elif self.cy < len(self.lines) - 1:
            self._push()
            self.lines[self.cy] = ln + self.lines.pop(self.cy + 1)
            self.modified = True

    def _tab(self):
        self._push()
        ln = self.lines[self.cy]
        self.lines[self.cy] = ln[:self.cx] + "    " + ln[self.cx:]
        self.cx += 4
        self.modified = True

    def _draw(self):
        self.stdscr.erase()
        self._draw_topbar()
        self._draw_editor()
        self._draw_statusbar()
        self._draw_keybar()
        self._scroll()
        scr_y = max(self.ETOP, min(self.cy - self.sy + self.ETOP, self.EBOT - 1))
        scr_x = max(self.GUTTER, min(self.cx - self.sx + self.GUTTER, self.W - 2))
        try:
            self.stdscr.move(scr_y, scr_x)
        except curses.error:
            pass
        self.stdscr.refresh()

    def _draw_topbar(self):
        fname = os.path.basename(self.filename) if self.filename else "untitled"
        mod   = " [+]" if self.modified else ""
        pk    = curses.color_pair(2) | curses.A_BOLD
        dm    = curses.color_pair(4) | curses.A_DIM
        self._wfill(0, "", curses.color_pair(1))
        self._w(0, 0,  "  ♦ ", pk)
        self._w(0, 4,  "orpheus", pk)
        self._w(0, 11, f"  —  {fname}{mod}", dm)

    def _draw_editor(self):
        nm = curses.color_pair(1)
        dm = curses.color_pair(4) | curses.A_DIM
        pk = curses.color_pair(2)
        for row in range(self.EH):
            li = row + self.sy
            sy = row + self.ETOP
            self._wfill(sy, "", nm)
            if li < len(self.lines):
                is_cur = (li == self.cy)
                lnum   = str(li + 1).rjust(3)
                self._w(sy, 0, lnum, pk if is_cur else dm)
                self._w(sy, 3, " ",  dm)
                line    = self.lines[li]
                visible = line[self.sx : self.sx + self.EW]
                self._draw_line(sy, self.GUTTER, visible, line)
            else:
                self._w(sy, 0, "  ~ ", dm)

    def _line_attr(self, full):
        s = full.lstrip()
        n = curses.color_pair(1)
        p = curses.color_pair(2)
        d = curses.color_pair(4) | curses.A_DIM
        if s.startswith("# "):
            return n | curses.A_BOLD
        if s.startswith(("## ", "### ")):
            return n | curses.A_BOLD | curses.A_UNDERLINE
        if s.startswith("> "):
            return d
        if s.startswith(("- ", "* ", "+ ")):
            return p
        if s.startswith("```") or s.startswith("---") or s.startswith("==="):
            return d
        if "**" in full or "__" in full:
            return p | curses.A_BOLD
        if "`" in full:
            return d
        return n

    def _draw_line(self, sy, x0, visible, full):
        attr  = self._line_attr(full)
        avail = max(0, self.W - x0 - 1)
        text  = visible[:avail].ljust(avail)
        try:
            self.stdscr.addstr(sy, x0, text, attr)
        except curses.error:
            pass

    def _draw_statusbar(self):
        msg  = self.msg if (time.time() - self.msg_time < 4) else ""
        loc  = f" {self.cy + 1}:{self.cx + 1} "
        attr = curses.color_pair(5)
        w    = max(1, self.W - 1)
        left = f"  {msg}"
        pad  = max(0, w - len(loc))
        bar  = left[:pad].ljust(pad) + loc
        self._wfill(self.H - 2, bar, attr)

    def _draw_keybar(self):
        dm   = curses.color_pair(4) | curses.A_DIM
        pk   = curses.color_pair(2)
        keys = [("^O","save"),("^X","quit"),("^R","open"),
                ("^W","find"),("^K","cut"),("^U","paste"),
                ("^Z","undo"),("^G","goto")]
        self._wfill(self.H - 1, "", dm)
        x = 1
        for key, label in keys:
            if x + len(key) + len(label) + 2 >= self.W - 1:
                break
            self._w(self.H - 1, x, key, pk | curses.A_BOLD)
            self._w(self.H - 1, x + len(key), f" {label}  ", dm)
            x += len(key) + len(label) + 3

    def run(self):
        while True:
            self._scroll()
            self._draw()
            ch = self.stdscr.getch()

            if ch == 24:                        # ctrl+x quit
                if self.modified:
                    ans = self._prompt("save before quit? (y/n): ")
                    if ans is None:
                        continue
                    if ans.strip().lower() == "y":
                        self._save()
                break
            elif ch == 15:  self._save()        # ctrl+o
            elif ch == 18:  self._open_file()   # ctrl+r
            elif ch == 23:  self._find()        # ctrl+w
            elif ch == 7:   self._goto()        # ctrl+g
            elif ch == 26:  self._undo()        # ctrl+z
            elif ch == 11:  self._cut()         # ctrl+k
            elif ch == 21:  self._paste()       # ctrl+u
            elif ch == 12:                      # ctrl+l end
                self.cy = len(self.lines) - 1
                self.cx = len(self.lines[self.cy])
            elif ch == 1:                       # ctrl+a start
                self.cy = 0; self.cx = 0
            elif ch in (10, 13):   self._enter()
            elif ch in (curses.KEY_BACKSPACE, 127, 8): self._bs()
            elif ch == curses.KEY_DC:           self._del()
            elif ch == 9:                       self._tab()
            elif ch == curses.KEY_UP:
                if self.cy > 0:
                    self.cy -= 1
                    self.cx = min(self.cx, len(self.lines[self.cy]))
            elif ch == curses.KEY_DOWN:
                if self.cy < len(self.lines) - 1:
                    self.cy += 1
                    self.cx = min(self.cx, len(self.lines[self.cy]))
            elif ch == curses.KEY_LEFT:
                if self.cx > 0:
                    self.cx -= 1
                elif self.cy > 0:
                    self.cy -= 1
                    self.cx = len(self.lines[self.cy])
            elif ch == curses.KEY_RIGHT:
                ln = self.lines[self.cy]
                if self.cx < len(ln):
                    self.cx += 1
                elif self.cy < len(self.lines) - 1:
                    self.cy += 1; self.cx = 0
            elif ch == curses.KEY_HOME:   self.cx = 0
            elif ch == curses.KEY_END:    self.cx = len(self.lines[self.cy])
            elif ch == curses.KEY_PPAGE:
                self.cy = max(0, self.cy - self.EH)
                self.cx = min(self.cx, len(self.lines[self.cy]))
            elif ch == curses.KEY_NPAGE:
                self.cy = min(len(self.lines) - 1, self.cy + self.EH)
                self.cx = min(self.cx, len(self.lines[self.cy]))
            elif ch == curses.KEY_RESIZE:
                curses.update_lines_cols()
            elif 32 <= ch <= 126:
                self._ins(chr(ch))


def main(stdscr):
    Orpheus(stdscr, sys.argv[1] if len(sys.argv) > 1 else None).run()

if __name__ == "__main__":
    curses.wrapper(main)