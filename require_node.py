import sublime_plugin
import os
from functools import partial


class RequireNodeCommand(sublime_plugin.TextCommand):
    def show(self, fileList, edit, x):
        file = self.view.file_name()
        fileWoExt = os.path.splitext(fileList[x])[0]
        moduleCandidateName = os.path.basename(fileWoExt)
        moduleRelPath = os.path.relpath(os.path.splitext(fileList[x])[0], os.path.dirname(file))

        if os.path.dirname(moduleRelPath) == "":
            moduleRelPath = "./" + moduleRelPath

        require_directive = "%s = require(\"%s\")" % (moduleCandidateName, moduleRelPath)

        for r in self.view.sel():
            self.view.replace(edit, r, require_directive)

    def run(self, edit):
        folder = self.view.window().folders()[0]
        fileList = []
        fullPathList = []

        for root, subFolders, files in os.walk(folder):
            for file in files:
                fullPathList.append(os.path.join(root, file))
                fileList.append([file, root.replace(folder, "", 1) or file])

        self.view.window().show_quick_panel(fileList, partial(self.show, fullPathList, edit))
