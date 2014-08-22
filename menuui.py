#-------------------------------------------------------------------------------
# Name:        menuui
# Purpose:     Menu-based command line UI
#
# Author:      Christopher Koch
#
# Created:     29/01/2013
# Copyright:   (c) Christopher Koch 2013
# Licence:     GPL 3.0
#-------------------------------------------------------------------------------

"""
This module defines classes and methods for creating text-based, menu-based
user interfaces.

The best way to use this module is to start by mapping out a tree of your menus
on paper, e.g.:
main(Menu)
    new game()
    load game(promptMenu)
    save game(promptMenu)
    options(Menu)
        optiona()
        optionb()
        optionc()
        restore()

The main types that you'll be using in this module are:
    Menu - options are basically functions
    PromptMenu - options return a value to the parent menu, which then does
                 something with them
    FileMenu - allows the user to navigate the filesystem, returning a file name
               and a directory name
"""

import os
import sys
import termutils


class MenuError(Exception):
    """Base class for exceptions in this module"""
    def __init__(self, obj, msg):
        self.obj = obj
        self.msg = msg

    def __str__(self):
        return "{}: {}".format(self.obj, self.msg)


class OptionError(MenuError):
    """Exception raised when there was an error adding an option to a menu"""
    pass


def confirm_quit(msg="Press enter to quit. "):
    """Wait for user to hit 'enter' before program close."""
    try:
        input(msg)
    except EOFError:
        pass
    termutils.reset_color()
    termutils.wipe()
    exit()


class MenuUI():
    """Initialize a menu-based application"""
    def __init__(self, prompt=' ? ', sep=':'):
        sys.ps1 = sys.ps2 = ''
        self.cols, self.rows = termutils.get_size()
        self.prompt = prompt
        self.sep = sep
        self.use_color_scheme()
        termutils.set_color(self.fg, self.bg)
        termutils.wipe()

    def use_color_scheme(self, scheme="default"):
        """Sets the following colors:
            fg, bg - global
            hdr_fg, hdr_bg - header
            dlg_fg, dlg_bg - dialog box
            but_fg, but_bg - buttons
            bdr_fg, bdr_bg - borders
            sel_fg, sel_bg - selection
            ps1_fg, ps1_bg - prompt
            dir_clr - directory
            file_clr - file
        """
        if scheme == "default":
            self.fg = 7
            self.bg = 0
            self.hdr_fg = 6
            self.hdr_bg = 0
            self.dlg_fg = 7
            self.dlg_bg = 4
            self.but_fg = 0
            self.but_bg = 7
            self.bdr_fg = 7
            self.bdr_bg = 4
            self.sel_fg = 7
            self.sel_bg = 1
            self.ps1_fg = 7
            self.ps1_bg = 0
            self.dir_clr = 3
            self.file_clr = 7
            termutils.set_bright()
        elif scheme == "curses":
            self.fg = 7
            self.bg = 4
            self.hdr_fg = 6
            self.hdr_bg = 4
            self.dlg_fg = 7
            self.dlg_bg = 4
            self.but_fg = 0
            self.but_bg = 7
            self.bdr_fg = 7
            self.bdr_bg = 4
            self.sel_fg = 7
            self.sel_bg = 1
            self.ps1_fg = 3
            self.ps1_bg = 4
            self.dir_clr = 3
            self.file_clr = 7
            termutils.set_bright()
        elif scheme == "as400":
            self.fg = 2
            self.bg = 0
            self.hdr_fg = 7
            self.hdr_bg = 0
            self.dlg_fg = 6
            self.dlg_bg = 0
            self.but_fg = 0
            self.but_bg = 6
            self.bdr_fg = 7
            self.bdr_bg = 6
            self.sel_fg = 0
            self.sel_bg = 7
            self.ps1_fg = 2
            self.ps1_bg = 0
            self.dir_clr = 5
            self.file_clr = 3
            termutils.set_bright()
        termutils.set_color(self.fg, self.bg)
        termutils.wipe()


class MenuOption():
    """A menu option"""
    def __init__(self, name, func):
        if isinstance(func, Menu):
            func = func.show
        if not hasattr(func, "__call__"):
            raise OptionError(self, "Menu options must be callable")
        self.name = str(name)
        self.func = func


class Menu():
    """A standard menu"""
    def __init__(self, ui, header):
        if not isinstance(ui, MenuUI):
            raise MenuError(ui, "Not a MenuUI object")
        self.ui = ui
        self.hdr = header
        self._opts = list()

    def add_option(self, opt):
        if not isinstance(opt, MenuOption) and opt is not None:
            raise OptionError(opt, "Not a MenuOption object")
        self._opts.append(opt)

    def show(self):
        # pgup = \xe0 I
        # pgdwn = \xe0 Q
        # bkspc = \x08
        self._paginate()
        i = 0
        cur_page = self._pages[i]
        choice = b''
        self._draw_page(cur_page)
        self._draw_ftr(i)
        k = b''
        while True:
            k = termutils.get_key()
            if k == b'\r':
                try:
                    opt = int(choice)
                    if self._opts[opt] is not None:
                        v = self._opts[opt].func()
                    else:
                        choice = b''
                        self._draw_ftr(i)
                        continue
                    if v is not None:
                        self._draw_page(cur_page)
                        self._draw_ftr(i)
                        termutils.set_pos(1, self.ui.rows - 1)
                        print(v, end='')
                        termutils.set_pos(len(self.ui.prompt) + 1, self.ui.rows - 3)
                        choice = b''
                        continue
                    else:
                        return "Library list changed"
                except ValueError:
                    choice = b''
                    self._draw_ftr(i)
                    continue
            if k == b'\xe0' or k == b'\x00':
                k += termutils.get_key()
            if k == b'\xe0Q':
                if i < len(self._pages):
                    i += 1
                    cur_page = self._pages[i]
                    self._draw_page(cur_page)
                    self._draw_ftr(i)
            elif k == b'\xe0I':
                if i > 0:
                    i -= 1
                    cur_page = self._pages[i]
                    self._draw_page(cur_page)
                    self._draw_ftr(i)
            elif k == b'\xe0\x86':
                return "Library list changed"
            # todo
            # if k == b'\x00;': display help
            elif not k.startswith(b'\xe0') and not k.startswith(b'\x00'):
                print(k.decode(), end='')
                choice += k

    def _draw_hdr(self):
        termutils.set_color(self.ui.hdr_fg, self.ui.hdr_bg)
        #termutils.set_pos(1, 1)
        print(self.hdr.center(self.ui.cols))

    def _draw_ftr(self, idx):
        termutils.set_pos(1, self.ui.rows - 3)
        termutils.set_color(self.ui.ps1_fg, self.ui.ps1_bg)
        print(self.ui.prompt, end='')
        termutils.set_color(self.ui.fg, self.ui.bg)
        print(' ' * (self.ui.cols - len(self.ui.prompt)), end='')

        if idx < len(self._pages) - 1:
            termutils.set_pos(self.ui.cols - 1, self.ui.rows - 4)
            termutils.set_color(self.ui.hdr_fg, self.ui.hdr_bg)
            print('+', end='')
        if idx > 0:
            termutils.set_pos(self.ui.cols - 3, self.ui.rows - 4)
            termutils.set_color(self.ui.hdr_fg, self.ui.hdr_bg)
            print('-', end='')
        termutils.set_pos(len(self.ui.prompt) + 1, self.ui.rows - 3)
        termutils.set_color(self.ui.fg, self.ui.bg)

    def _draw_page(self, page):
        sep = self.ui.sep
        termutils.wipe()
        self._draw_hdr()
        termutils.set_color(self.ui.fg, self.ui.bg)
        for i, opt in enumerate(page):
            if opt is None:
                print('')
                continue
            print("{}{} {}".format(i, sep, opt.name))

    def _paginate(self):
        num_opts = self.ui.rows - 7
        pages = [[]]
        cur_page = 0
        opts = self._opts
        for i in opts:
            if len(pages[cur_page]) < num_opts:
                pages[cur_page].append(i)
            else:
                pages.append(list())
                cur_page += 1
                pages[cur_page].append(i)
        self._pages = pages

if __name__ == "__main__":
    ui = MenuUI()
    ui.use_color_scheme("curses")
    main_menu = Menu(ui, "FooBarBaz")
    def foo():
        return "Foo!"
    def bar():
        return "Bar!"
    def baz():
        return "Baz"
    def thang():
        termutils.wipe()
        confirm_quit()
    main_menu.add_option(MenuOption("Foo", foo))
    main_menu.add_option(MenuOption("Bar", bar))
    main_menu.add_option(None)
    main_menu.add_option(MenuOption("Baz", baz))
    sub_menu = Menu(ui, "This is a submenu")
    sub_menu.add_option(None)
    sub_menu.add_option(MenuOption("Quit", thang))
    main_menu.add_option(None)
    main_menu.add_option(MenuOption("Another menu", sub_menu))
    main_menu.add_option(None)
    main_menu.add_option(MenuOption("Quit", thang))
    main_menu.show()
    confirm_quit()