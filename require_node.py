import sublime_plugin
import os
from functools import partial


class RequireNodeCommand(sublime_plugin.TextCommand):
    def show(self, fileList, edit, x):
        file = self.view.file_name()
        file_wo_ext = os.path.splitext(fileList[x])[0]
        module_candidate_name = os.path.basename(file_wo_ext).replace(".", "")
        module_rel_path = os.path.relpath(file_wo_ext, os.path.dirname(file))

        if os.path.dirname(module_rel_path) == "":
            module_rel_path = "./" + module_rel_path

        require_directive = "%s = require(\"%s\")" % (module_candidate_name, module_rel_path)

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
