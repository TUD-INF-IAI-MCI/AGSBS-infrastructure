# -*- coding: utf-8 -*-
import sublime, sublime_plugin
import os
import re
import codecs, re, sys
import collections
import json

from MAGSBS import *

class CreateStructureCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        sublime.windows()[0].show_input_panel("Was bearbeiten Sie", "Buch|Kapitelanzahl fuer ein Buch oder Thema der Vorlesungsfolie", self.on_done, self.on_change, self.on_cancel)
       
    def on_done(self, input):
        str = input.split('|')
        path = sublime.windows()[0].folders()[0]
        if str[0].lower() == "buch":
            number_of_capitals = str[1]
            create_folder_structure_book(path, number_of_capitals)        
        else:
            lecture_name = input.replace(" ","_")
            create_folder_structure_lecture(path, lecture_name)

    def on_change(self, input):
        #  if user cancels with Esc key, do nothing
        #  if canceled, index is returned as  -1
        if input == -1:
            return
    def on_cancel(self, input):
        #  if user cancels with Esc key, do nothing
        #  if canceled, index is returned as  -1
        if input == -1:
            return
"""
count md files in path
"""
def count_md_file(path):
    count = 0
    for directoryname, directory_list, file_list in os.walk(path):
        for file in file_list:                        
            if file.endswith('.md'):
                count = count + 1
                
    return count

def create_folder_structure_lecture(path, name):    
    filecount = count_md_file(path)
    if filecount < 10:
        name = "vorlesung_0" +str(filecount+1) +"_"+name
    else:
        name = "vorlesung_" +str(filecount) +"_"+name
    """
     name = vorlesung_xx_name_der_vorlesung
    """
    create_md_file(path, name)


"""
    input ist die anzahl der Kapitel
"""
def create_folder_structure_book(path, input):
    input_int = int(input)
    i = 1
    k_str = ""
    while i <= input_int:
        if i < 10:
            k_str ="k0" + str(i)
        else:
            k_str = "k" + str(i)        
        filename = k_str
        print "filename "+filename
        print "k_str "+k_str
        create_n_folder(path, filename)
        i = i + 1        

def create_md_file(foldername, filename):
    fn  = foldername + os.sep +filename  +".md"
    fd = os.open(fn, os.O_RDWR|os.O_CREAT) 
    print "---------- text "
    text = "Fuegen Sie hier die ueberschrift ein \n============= " 
    #text = text.decode('utf-8')
    #os.write(fd, text.encode('utf-8'))
    os.write(fd, text)    
    os.close(fd)   

def create_n_folder( foldername, filename):
        if not os.path.exists(foldername):
            parent = os.path.split(foldername)[0]
            if not os.path.exists(parent):
                create_folder(parent, filename)                
        #if os.path.exists(foldername):
        """
         path =  buch/k01
        """
        path = foldername +os.sep +filename
        os.mkdir(path) 
        os.mkdir(path+os.sep+"bilder") 
        create_md_file(path, filename)                       
        

"""
{ "keys": ["ctrl+alt+n"], "command": "create_structure", "args": {"tag": ""} },
"""
class CreateFolderPanelCommand(sublime_plugin.TextCommand):
    def run(self, arg, tag):
        self.view.window().show_input_panel("Kapitelanzahl", "", self.on_done, self.on_change, self.on_cancel)
       
        #create_File(filename+"/text.md", "Helloworld")
    def on_done(self, input):
        #  if user cancels with Esc key, do nothing
        #  if canceled, index is returned as  -1
        if input == -1:
            return
        path = self.view.file_name()
        base = os.path.split(path)[0]
        if not input.isdigit():
            return
        input_int = int(input)
        i = 1
        k_str = ""
        while i <= input_int:
            if i < 10:

                k_str = "/k0" + str(i)
            else:
                k_str = "/k" + str(i)
            foldername = base + k_str
            filename = k_str+ ".md"
            self.create_n_folder(foldername, filename)
            i = i + 1
        #create folder and kapitel md
        #self.view.insert(edit, target, "filename") 
       # create_File(filename+"/text.md", "Helloworld")
    def on_change(self, input):
        #  if user cancels with Esc key, do nothing
        #  if canceled, index is returned as  -1
        if input == -1:
            return
    def on_cancel(self, input):
        #  if user cancels with Esc key, do nothing
        #  if canceled, index is returned as  -1
        if input == -1:
            return

    def create_n_folder(self, foldername, filename):
        if not os.path.exists(foldername):
            parent = os.path.split(foldername)[0]
            if not os.path.exists(parent):
                self.create_folder(parent, filename)
        os.mkdir(foldername)
        fn  = foldername + filename        
        fd = os.open(fn, os.O_RDWR|os.O_CREAT)        
        os.write(fd, "Fuegen Sie hier die Überschrift ein \n")
        os.write(fd, "============= \n")
        os.close(fd)



    def create_File(filename, text):
        v = sublime.version()
        if v >= '3000':
            f = open(filename, 'w', encoding='utf-8')
            f.write(text)
            f.close()
        else: # 2.x
            f = open(filename, 'w')
            f.write(text.encode('utf-8'))
            f.close()

class AddTagCommand(sublime_plugin.TextCommand):
     def run(self, edit, tag, markdown_str):
        screenful = self.view.visible_region()
        (row,col) = self.view.rowcol(self.view.sel()[0].begin())
        target = self.view.text_point(row, 0)
        if tag in ['h', 'em', 'strong']:
                self.view.insert(edit, target, markdown_str)
                (row,col) = self.view.rowcol(self.view.sel()[0].begin()) 
                word = self.view.word(target)
                movecursor = len(word)   
                diff = 0
                if movecursor > 0:
                    diff = movecursor/2        
                strg = str(diff)
                #elf.view.insert(edit, target, strg)
                target = self.view.text_point(row, diff)
                self.view.sel().clear()
                self.view.sel().add(sublime.Region(target))
                self.view.show(target)

        elif tag in ['blockquote', 'ul', 'ol', 'code']:
            self.view.insert(edit, target, markdown_str)

        elif tag in ['hr']:
            self.view.insert(edit, target, markdown_str +"\n")
        elif tag in ['table']:
            self.view.insert(edit, target, "| Tables        | Are           | Cool  | \n" 
            "| ------------- | ------------- | ----- |\n" 
            "| col 3 is      | right-aligned | $1600 |\n"
            "| col 2 is      | centered      |   $12 |\n"
            "| zebra stripes | are neat      |    $1 |\n")


class InsertPanelCommand(sublime_plugin.TextCommand):
    def run(self, edit, tag):
        if tag == 'img':
            self.view.window().show_input_panel("Bild-URL", "Bild-URL_eintragen", self.on_done_img, self.on_change, self.on_cancel)
        elif tag =='a':
            self.view.window().show_input_panel("Link-URL", "Link_eintragen", self.on_done_link, self.on_change, self.on_cancel)
        elif tag =='a name':
            self.view.window().show_input_panel("Ankername", "Anker_eintragen", self.on_done_anchor, self.on_change, self.on_cancel)
        elif tag =='page':
            self.view.window().show_input_panel("Seitenzahl", "", self.on_done_page, self.on_change, self.on_cancel)
    def on_done_page(self, input):
        #  if user cancels with Esc key, do nothing
        #  if canceled, index is returned as  -1
        if input == -1:
            return
       # if user picks from list, return the correct entry
        print "------ \t" +input
        markdown = '######- Seite ' +input +' -######'
        self.view.run_command(
            "insert_my_text", {"args":            
            {'text': markdown}})
    def on_done_img(self, input):
        #  if user cancels with Esc key, do nothing
        #  if canceled, index is returned as  -1
        if input == -1:
            return
       # if user picks from list, return the correct entry
        print "------ \t" +input
        markdown = '![Alternativtext]  (' +input +')'
        self.view.run_command(
            "insert_my_text", {"args":            
            {'text': markdown}})

    def on_done_anchor(self, input):
        #  if user cancels with Esc key, do nothing
        #  if canceled, index is returned as  -1
        if input == -1:
            return
       # if user picks from list, return the correct entry
        markdown = '<a name=\"' +input +'\"></a>'
        self.view.run_command(
            "insert_my_text", {"args":            
            {'text': markdown}})

    def on_done_link(self, input):
        #  if user cancels with Esc key, do nothing
        #  if canceled, index is returned as  -1
        if input == -1:
            return
       # if user picks from list, return the correct entry
        markdown = '[Alternativtext](' +input +')'
        self.view.run_command(
            "insert_my_text", {"args":            
            {'text': markdown}})

    def on_change(self, input):
          if input == -1:
            return

    def on_cancel(self, input):
        if input == -1:
            return

class Move_caret_topCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        screenful = self.view.visible_region()

        col = self.view.rowcol(self.view.sel()[0].begin())[1]
        row = self.view.rowcol(screenful.a)[0] + 1
        target = self.view.text_point(row, col)

        self.view.sel().clear()
        self.view.sel().add(sublime.Region(target))
    def on_done(self, input):
 
        #  if user cancels with Esc key, do nothing
        #  if canceled, index is returned as  -1
        if input == -1:
            return

 
        # if user picks from list, return the correct entry
        image_markdown = '![Alternativtext]  (' +input +')'
        self.view.run_command(
            "insert_my_text", {"args":            
            {'text': image_markdown}})

    def on_change(self, input):
          if input == -1:
            return
    def on_cancel(self, input):
        if input == -1:
            return

class InsertMyText(sublime_plugin.TextCommand):
 
    def run(self, edit, args):
 
        # add this to insert at current cursor position
        # http://www.sublimetext.com/forum/viewtopic.php?f=6&t=11509
 
        self.view.insert(edit, self.view.sel()[0].begin(), args['text'])


class Move_caret_middleCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        screenful = self.view.visible_region()

        col = self.view.rowcol(self.view.sel()[0].begin())[1]
        row_a = self.view.rowcol(screenful.a)[0]
        row_b = self.view.rowcol(screenful.b)[0]

        middle_row = (row_a + row_b) / 2
        target = self.view.text_point(middle_row, col)

        self.view.sel().clear()
        self.view.sel().add(sublime.Region(target))

class Move_caret_bottomCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        screenful = self.view.visible_region()

        col = self.view.rowcol(self.view.sel()[0].begin())[1]
        row = self.view.rowcol(screenful.b)[0] - 1
        target = self.view.text_point(row, col)

        self.view.sel().clear()
        self.view.sel().add(sublime.Region(target))

class Move_caret_forwardCommand(sublime_plugin.TextCommand):
    def run(self, edit, nlines):
        screenful = self.view.visible_region()

        (row,col) = self.view.rowcol(self.view.sel()[0].begin())
        target = self.view.text_point(row+nlines, col)

        self.view.sel().clear()
        self.view.sel().add(sublime.Region(target))
        self.view.show(target)

class Move_caret_backCommand(sublime_plugin.TextCommand):
    def run(self, edit, nlines):
        screenful = self.view.visible_region()

        (row,col) = self.view.rowcol(self.view.sel()[0].begin())
        target = self.view.text_point(row-nlines, col)

        self.view.sel().clear()
        self.view.sel().add(sublime.Region(target))
        self.view.show(target)


"""
 Erweiterung basierend auf Sebastians Code
 fuehrt sebastians erweiterung aus und speichert inhalt in inhalt.md ab
"""
class CreateTocFileCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        foldername = sublime.windows()[0].folders()[0] 
        base = foldername
        self.__dir = base        
        c = create_index(base)
        
        c.walk()        
        index = c.get_index()
        md_index = index2markdown_TOC(index)
        WriteIndex2File(base,md_index.get_markdown_page())

#erfordert datei
class CreateTocCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        path = self.view.file_name()
        base = os.path.split(path)[0]
        print "base CreateTocCommand" +base
        self.__dir = base

        # for root, dirs, files in os.walk(base):
        #     for folder in dirs:
        #         print folder
        # collect_all_md_files(base)   
        #test_file_walk()
        c = create_index(base)
        c.walk()
        index = c.get_index()
        md_index = index2markdown_TOC(index)
        WriteIndex2File(base,md_index.get_markdown_page())        
        # window.run_command("save")
        # window.run_command("reload")


class SaveAndReloadCommand(sublime_plugin.WindowCommand):
    def run(self):                        
        self.window.run_command("reload_view")
        #self.window.run_command("save")
        


       
def WriteIndex2File(base,content):

    indexFile = base + os.sep + "index.md"
    print "Save 2 file " +indexFile
    fd = os.open(indexFile, os.O_RDWR|os.O_CREAT)
    text = content.encode('utf-8').strip()
    os.write(fd, content)
    os.close(fd)

# def collect_all_md_files(base):
#     md_files = []
#     kap_folder = []
#     for root, dirs, files in os.walk(base):         
#         for f in files:
#             if f.find("md") >= 0:                
#                 md_files.append(f)
#         for folder in dirs:
#             if folder.find("k") >= 0:
#                 kap_folder.append(folder)
#     return md_files

def test_markdown_parser():
    m = markdownParser("Heya\n====\n\nImportant advisories\n---------\n\n\n###### - Seite 6 -\n")
    m.parse()
    for item in m.get_data():
        print(repr(item))
    print("Done.")

def test_file_walk():    
    c = create_index('.')
    c.walk()
    for key, value in c.get_index().items():
        print(key+repr(value)+'\n\n')
    return c.get_index()

# -- if not imported but run as main module, test functionality --

def test_index2markdown_TOC():
    print "test_index2markdown_TOC"
    idx = test_file_walk()
    c = index2markdown_TOC(idx, 'de')
    print(c.get_markdown_page())

if __name__ == '__main__':
    #test_markdown_parser()
    #test_file_walk()
    test_index2markdown_TOC()
