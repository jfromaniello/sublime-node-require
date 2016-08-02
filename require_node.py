import sublime
import sublime_plugin
import os
import sys

if sys.version_info[0] == 2:
    from Edit import Edit as Edit
else:
    from .Edit import Edit as Edit

SETTINGS = 'Require CommonJS Modules Helper.sublime-settings'

class RequireNodeCommand(sublime_plugin.TextCommand):
    def write_require(self, resolvers):
        current_lang = self.view.scope_name(self.view.sel()[0].a).split(' ')[0]

        def write(index):
            if index == -1:
                return
            [module_candidate_name, module_name] = resolvers[index]()

            settings = sublime.load_settings(SETTINGS)

            known_requires = settings.get('known_requires')
            module_candidate_name = known_requires.get(module_name, module_candidate_name)

            if module_candidate_name.find("-") != -1:
                upperWords = [word.capitalize() for word in module_candidate_name.split("-")[1::]]
                module_candidate_name = "".join(module_candidate_name.split("-")[0:1] + upperWords)

            region_to_insert = self.view.sel()[0]

            line_is_empty = self.view.lines(region_to_insert)[0].empty()

            clause_formats = {
                "source.js": {
                    True:  settings.get('source_js_new_line'),
                    False: settings.get('source_js_existing_line')
                },
                "source.coffee": {
                    True:  settings.get('source_coffee_new_line'),
                    False: settings.get('source_coffee_existing_line')
                },
                "text.html.riot": {
                    True:  settings.get('source_js_new_line'),
                    False: settings.get('source_js_existing_line')
                }
            }

            require_directive = clause_formats[current_lang][line_is_empty].format(module_candidate_name, get_path(module_name))

            with Edit(self.view) as edit:
                edit.insert(region_to_insert.a, require_directive)

        def get_path(path):
            quotes_type = sublime.load_settings(SETTINGS).get('quotes_type')
            quote = "\"" if quotes_type == "double" else "'"
            return quote + path + quote

        return write

    def resolve_from_file(self, full_path):
        def resolve():
            file = self.current_file
            file_wo_ext = os.path.splitext(full_path)[0]
            module_candidate_name = os.path.basename(file_wo_ext).replace(".", "")
            module_rel_path = os.path.relpath(file_wo_ext, os.path.dirname(file))

            if module_rel_path[:3] != ".." + os.path.sep:
                module_rel_path = "." + os.path.sep + module_rel_path

            return [module_candidate_name, module_rel_path.replace(os.path.sep, "/")]
        return resolve

    def get_suggestion_from_nodemodules(self):
        resolvers = []
        suggestions = []
        current_file_dirs = self.current_file.split(os.path.sep)
        current_dir = os.path.split(self.current_file)[0]
        for x in range(len(self.view.window().folders()[0].split(os.path.sep)), len(current_file_dirs))[::-1]:
            candidate = os.path.join(current_dir, "node_modules")
            if os.path.exists(candidate):
                for dir in [name for name in os.listdir(candidate)
                                 if os.path.isdir(os.path.join(candidate, name)) and name != ".bin"]:
                    resolvers.append(lambda dir=dir: [dir, dir])
                    suggestions.append("module: " + dir)
                break
            current_dir = os.path.split(current_dir)[0]
        return [resolvers, suggestions]

    def get_suggestion_native_modules(self):
        node_native = sublime.load_settings(SETTINGS).get('node_native')
        result = [[(lambda ni=ni: [ni, ni]) for ni in node_native],
                ["native: " + ni for ni in node_native]]

        return result

    def run(self, edit):
        self.edit = edit
        self.current_file = self.view.file_name()

        folder = self.view.window().folders()[0]
        suggestions = []
        resolvers = []

        #create suggestions for all files in the project
        for root, subFolders, files in os.walk(folder, followlinks=True):
            if root.startswith(os.path.join(folder, "node_modules")):
                continue
            if root.startswith(os.path.join(folder, ".git")):
                continue
            for file in files:
                if file == "index.js" or file == "index.coffee":
                    resolvers.append(self.resolve_from_file(root))
                    suggestions.append([os.path.split(root)[1], root])
                    continue
                resolvers.append(self.resolve_from_file(os.path.join(root, file)))
                suggestions.append([file, root.replace(folder, "", 1) or file])

        #create suggestions for modules in node_module folder
        [resolvers_from_nm, suggestions_from_nm] = self.get_suggestion_from_nodemodules()
        resolvers += resolvers_from_nm
        suggestions += suggestions_from_nm

        #create suggestions from native modules
        [resolvers_from_native, suggestions_from_nm] = self.get_suggestion_native_modules()
        resolvers += resolvers_from_native
        suggestions += suggestions_from_nm

        self.view.window().show_quick_panel(suggestions, self.write_require(resolvers))
