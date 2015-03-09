import sublime
import sublime_plugin
import os
import sys

if sys.version_info[0] == 2:
    from Edit import Edit as Edit
else:
    from .Edit import Edit as Edit


NODE_NATIVE = [
    'assert',
    'buffer',
    'child_process',
    'console',
    'constants',
    'crypto',
    'cluster',
    'dgram',
    'dns',
    'domain',
    'events',
    'freelist',
    'fs',
    'http',
    'https',
    'module',
    'net',
    'os',
    'path',
    'punycode',
    'querystring',
    'readline',
    'repl',
    'stream',
    'string_decoder',
    'sys',
    'timers',
    'tls',
    'tty',
    'url',
    'util',
    'vm',
    'zlib'
]

class RequireNodeCommand(sublime_plugin.TextCommand):
    def write_require(self, resolvers):

        current_lang = self.view.scope_name(self.view.sel()[0].a).split(' ')[0]

        clause_formats = {
            "source.js": {
                True:  "var {0} = require({1});",
                False: "require({1})"
            },
            "source.coffee": {
                True:  "{0} = require {1}",
                False: "require {1}"
            }
        }

        def write(index):
            if index == -1:
                return
            [module_candidate_name, module_rel_path] = resolvers[index]()

            if module_candidate_name.find("-") != -1:
                upperWords = [word.capitalize() for word in module_candidate_name.split("-")[1::]]
                module_candidate_name = "".join(module_candidate_name.split("-")[0:1] + upperWords)

            region_to_insert = self.view.sel()[0]

            line_is_empty = self.view.lines(region_to_insert)[0].empty()

            require_directive = clause_formats[current_lang][line_is_empty].format(module_candidate_name, get_path(module_rel_path))

            with Edit(self.view) as edit:
                edit.insert(region_to_insert.a, require_directive)

        def get_path(path):
            settings = sublime.load_settings(__name__ + '.sublime-settings')
            quotes_type = settings.get('quotes_type')
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
        result = [[(lambda ni=ni: [ni, ni]) for ni in NODE_NATIVE],
                ["native: " + ni for ni in NODE_NATIVE]]

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
