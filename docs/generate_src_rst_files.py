# This file is the first stage of the documentation building pipeline
# It is used to generate files with content using code that can be used by the sphinx builder to create pages

import os
import string
import shutil
import argparse
import json
import logging
try:
    # from supported_devices import get_flags
    get_flags = lambda x: ((), False)
except (ImportError, ModuleNotFoundError) as e:
    logging.warning("supported_device.py does not exist")

# These directories are not explored recursively while generating content for it.
EXCLUDED_MODULES = ["exceptions", "library_getter", "setup", "__init__"]
EXCLUDED_DIRS = [".pytest_cache", "docs", "tests", "__pycache__"]
ARRAY_CONTAINER_SUBMODULES_TO_SKIP = ["container", "wrapping"]

THIS_DIR = ""
SUBMODULE_TITLE = ""
ROOT_DIR = ""
SUBMOD_ORDERS = dict()
SUBMODS_TO_SKIP = list()
SUBMODS_TO_STEP = list()
IVY_ONLY = False

DISCORD_URL = "https://discord.com/channels/799879767196958751/"

DISCUSSION_MSG =  (".. _`discord`: https://discord.gg/ZVQdvbzNQJ \n" 
                  ".. _`{submodule_name} forum`: {discord_forum_link}\n" 
                 ".. _`{submodule_name} channel`: {discord_channel_link}\n" 
                  "This should have hopefully given you an overview of the {submodule_name} submodule,"
                  "If you have any questions, please feel free to reach out on our "
                  "`discord`_ in the `{submodule_name} channel`_ or in the `{submodule_name} forum`_!")

DEVICE_SUPPORT_STR = """
.. list-table:: Device Support
   :widths: 20 20 20 20 20
   :header-rows: 1

   * - Device
     - JAX
     - NumPy
     - TensorFlow
     - PyTorch
   * - CPU
     - {}
     - {}
     - {}
     - {}
   * - GPU
     - {}
     - {}
     - {}
     - {}
"""

with open("partial_source/supported_frameworks.rst") as fw_file:
    SUPPORTED_FRAMEWORKS = fw_file.read()

def write_discussion_links():
    with open("partial_source/discussion_links.json", "r") as f:
        modules = json.load(f)
    for module in modules:
        submodules = modules[module]
        for submodule in submodules:
            fpath = "autogenerated_source/" + module + "/" + submodule + ".rst"
            discord_channel_url = DISCORD_URL  + submodules[submodule][0]
            discord_forum_url = DISCORD_URL + submodules[submodule][1]
            with open(fpath, "a") as rst_file:
                rst_file.write(DISCUSSION_MSG.format(
                    submodule_name=submodule.replace('_', ' '),
                    discord_forum_link=discord_forum_url,
                    discord_channel_link=discord_channel_url
                ))

def remove_absolute_img_links(readme_contents):
    lines = readme_contents.split("\n")
    new_lines = list()
    for line in lines:
        new_line = line
        squashed_line = line.replace(" ", "")
        if (
            len(squashed_line) >= 28
            and squashed_line[0:28] == "..image::https://github.com/"
            and "docs/partial_source" in squashed_line
        ):
            pre, post = line.split("docs/partial_source")
            pre = pre.split("https")[0]
            new_line = "docs/partial_source".join([pre, post])
        new_lines.append(new_line)
    return "\n".join(new_lines)


def create_index_rst(sub_contents_dict):
    prepend_filepath = "partial_source/index_prepend.rst"
    with open(prepend_filepath) as file:
        prepend_data = file.read()

    with open("../README.rst") as file:
        readme_contents = file.read()
    readme_contents = readme_contents.replace("Check out the docs_ for more info!", "")
    readme_contents = readme_contents.replace(
        '</div>\n    <br clear="all" />\n',
        '</div>\n    <br clear="all" />\n    <br/>\n    <br/>\n',
    )
    readme_contents = remove_absolute_img_links(readme_contents)
    readme_contents = readme_contents.replace(
        "docs/partial_source/", "../autogenerated_source/"
    )
    readme_contents = readme_contents.replace(
        "../autogenerated_source/logos/supported/", "_images/"
    )
    readme_contents = readme_contents.replace(
        "../autogenerated_source/logos/", "_images/"
    )
    readme_contents = readme_contents.replace(
        "../autogenerated_source/images/", "_images/"
    )

    append_filepath = "partial_source/index_append.rst"
    if os.path.exists(append_filepath):
        with open(append_filepath) as file:
            append_data = file.read()
    else:
        append_data = ""

    all_data = prepend_data + "\n" + readme_contents + "\n" + append_data

    with open("autogenerated_source/index.rst", "w+") as file:
        file.write(all_data)

    # toctree dict
    toctree_dict = dict()
    for key, value in sub_contents_dict.items():
        new_key = key.split("/")[-1]
        new_value = [item.split("/")[-1].replace(".py", "") + ".rst" for item in value]
        toctree_dict[new_key] = new_value

    if SUBMODULE_TITLE is not None:
        # append toctree
        append_toctree_to_rst(
            toctree_dict, "autogenerated_source/index.rst", SUBMODULE_TITLE
        )
        toctree_dict = dict()

    with open(os.path.join(THIS_DIR, "ivy_modules.txt"), "r") as f:
        module_names = [line.replace("\n", "") for line in f.readlines()]

    toctree_dict["docs"] = [mod_name + ".rst" for mod_name in module_names]
    os.makedirs("autogenerated_source/docs", exist_ok=True)
    for fname in toctree_dict["docs"]:
        with open("autogenerated_source/docs/{}".format(fname), "w+") as file:
            title_str = fname[:-4].replace("_", " ").capitalize()
            file.write(title_str + "\n" + "=" * len(title_str))

    # append toctree
    append_toctree_to_rst(toctree_dict, "autogenerated_source/index.rst")


def append_toctree_to_rst(toctree_dict, rst_path, caption=None, newlines=True):
    # appends the rst files generated for a module in module_name.rst
    str_to_write = "\n"
    for key, list_of_rsts in toctree_dict.items():
        cap = key.capitalize().replace("_", " ") if caption is None else caption

        # New headings
        # Functional --> Functions
        # Stateful --> Classes
        if cap == "Functional":
            cap = "Functions"

        str_to_write += (
            "\n.. toctree::\n   :hidden:\n   :maxdepth: -1\n   :caption: "
            + cap
            + "\n\n"
        )
        for rst_filename in list_of_rsts:
            str_to_write += "   " + os.path.join(key, rst_filename) + "\n"
        str_to_write += "\n"

    if not newlines:
        str_to_write = str_to_write.lstrip("\n")
        str_to_write += "\n"

    with open(rst_path, "a") as file:
        file.write(str_to_write)

def copy_readme_to_rst(readme_path, rst_path):
    # copy data from README.rst to module_name.rst
    with open(readme_path) as file:
        readme_contents = file.read()
    with open(rst_path, "w+") as file:
        file.write(readme_contents)


def add_array_and_container_code(module_str, module_path, dotted_namespace):
    folder = module_path[0 : module_path.rfind("/")]
    content = module_str.split("\n")

    # Find setup statements
    setup_statements = []
    for line in content:
        if line[0:6] != "class ":
            setup_statements.append(line)
        else:
            break

    file = None
    file_to_modify = {
        ".array.": os.path.join(folder, "array_methods.py"),
        ".container.": os.path.join(folder, "container_methods.py"),
    }

    # Decide the file to be modified
    if ".array." in dotted_namespace:
        file = file_to_modify[".array."]
    elif ".container." in dotted_namespace:
        file = file_to_modify[".container."]
    else:
        return

    # Append file
    with open(file, "a") as f:
        # Add submodule name at the top of file
        f.write("#{}\n".format(dotted_namespace))

        # Add setup statements to the file
        for line in setup_statements:
            f.write("{}\n".format(line))

        # Add function signature and docstrings
        find_def, find_docstring, done, inside_nest = True, False, False, False
        i = 0
        while i < len(content):
            line = content[i]
            line = line.strip("\n")

            # Find function signature
            if find_def:
                if line[0:8] == "    def " and not inside_nest:
                    while (
                        "):" not in line
                        and "ivy.Array:" not in line
                        and "ivy.Container:" not in line
                    ):
                        f.write("{}\n".format(line[4:]))
                        i += 1
                        if i == len(content):
                            return
                        line = content[i]
                    f.write("{}\n".format(line[4:]))
                    i += 1
                    find_docstring = True
                    find_def = False
                elif line[0:4] == "def ":
                    i += 1
                    inside_nest = True
                    continue
                else:
                    i += 1
                    continue

            # Find docstring
            elif find_docstring:
                if "'''" in line or '"""' in line:
                    f.write("{}\n".format(line[4:]))
                    i += 1
                    if i == len(content):
                        return
                    line = content[i]
                    while "'''" not in line and '"""' not in line:
                        f.write("{}\n".format(line[4:]))
                        i += 1
                        if i == len(content):
                            return
                        line = content[i]
                    f.write("{}\n".format(line[4:]))
                    find_docstring = False
                    done = True
                else:
                    i += 1
                    f.write("    pass\n\n\n")
                    find_def, find_docstring, done = True, False, False

            # Add pass to the end of each function
            elif done:
                i += 1
                if not inside_nest:
                    f.write("    pass\n\n\n")
                find_def, find_docstring, done, inside_nest = True, False, False, False
            else:
                i += 1


def add_instance_and_static_methods(directory):
    # get contents of directory, here directory refers to the ivy directory
    contents = os.listdir(directory)
    contents.sort()

    # save dir in docs
    repo_name = ROOT_DIR.split("/")[-1]

    repo_location = directory.find(repo_name)

    name_len_p1 = len(repo_name) + 1

    # represent as file-paths
    cont_paths = [os.path.join(directory, item) for item in contents]

    # Get all sub-directories inside the directory which are not to be excluded
    sub_dirs = [
        item
        for item in cont_paths
        if os.path.isdir(item) and item.split("/")[-1] not in EXCLUDED_DIRS
    ]

    # Recursively access all sub-directories,
    # and store the list of sub directories and sub modules for that directory in the dictionary
    for sub_dir in sub_dirs:
        if sub_dir in [os.path.join(ROOT_DIR, sts) for sts in SUBMODS_TO_SKIP]:
            continue
        add_instance_and_static_methods(sub_dir)

    # Extract python modules which are not to be excluded
    modules = [
        item
        for item in cont_paths
        if item[-3:] == ".py" and item.split("/")[-1][:-3] not in EXCLUDED_MODULES
    ]

    for module in modules:

        # determine number of submodule folders to traverse
        full_rel_path = module[repo_location + name_len_p1 :]
        num_rsts_to_create = full_rel_path.count("/") + 1

        for i in range(num_rsts_to_create):
            # determine number of submodule folders to traverse
            full_rel_path = module[repo_location + name_len_p1 :]

            # Dotted namespace
            dotted_namespace = "/".join(
                module[repo_location:-3].split("/")[0 : i + 3]
            ).replace("/", ".")

        with open(module, errors="replace") as file:
            module_str = file.read()

        index = module_str.find("\n    def ")
        if index != -1:
            add_array_and_container_code(module_str, module, dotted_namespace)


def get_functions_and_classes(module_path, dotted_namespace):
    # This function finds all classes and functions in a module using 'class' and 'def' keywords
    with open(module_path, errors="replace") as file:
        module_str = file.read()
    all_function_names = [
        dotted_namespace + "." + item.split("(")[0]
        for item in module_str.split("\ndef ")[1:]
    ]
    public_function_names = [
        n for n in all_function_names if n.split(".")[-1][0] != "_"
    ]
    class_names = [
        dotted_namespace + "." + item.split("(")[0]
        for item in module_str.split("\nclass ")[1:]
    ]
    return public_function_names, class_names


def create_rst_files(directory):
    # get contents of directory, here directory refers to the ivy directory
    contents = os.listdir(directory)
    contents.sort()

    # represent as file-paths
    cont_paths = [os.path.join(directory, item) for item in contents]

    # save dir in docs
    repo_name = ROOT_DIR.split("/")[-1]

    repo_location = directory.find(repo_name)

    name_len_p1 = len(repo_name) + 1

    # Extracting the folder name from the repo path
    doc_save_dir = os.path.join(
        "autogenerated_source", directory[repo_location + name_len_p1 :]
    )

    # Creating a folder with that name inside autogenerated_source
    os.makedirs(os.path.dirname(doc_save_dir), exist_ok=True)

    # Get all sub-directories inside the directory which are not to be excluded
    sub_dirs = [
        item
        for item in cont_paths
        if os.path.isdir(item) and item.split("/")[-1] not in EXCLUDED_DIRS
    ]

    # Dictionary to store all submodules for which rst files are generated
    sub_contents = dict()

    # Recursively access all sub-directories,
    # and store the list of sub directories and sub modules for that directory in the dictionary
    for sub_dir in sub_dirs:
        if sub_dir in [os.path.join(ROOT_DIR, sts) for sts in SUBMODS_TO_SKIP]:
            continue
        sub_sub_dirs, sub_modules = create_rst_files(sub_dir)
        sub_contents[sub_dir] = sub_sub_dirs + sub_modules

    # Extract python modules which are not to be excluded
    modules = [
        item
        for item in cont_paths
        if item[-3:] == ".py" and item.split("/")[-1][:-3] not in EXCLUDED_MODULES
    ]
    # get classes and functions for these modules
    for module in modules:

        # determine number of submodule folders to traverse
        full_rel_path = module[repo_location + name_len_p1 :]
        num_rsts_to_create = full_rel_path.count("/") + 1
        for i in range(num_rsts_to_create):

            # relative path
            rel_path = "/".join(full_rel_path.split("/")[0 : i + 2])

            # This prevents creation of folder structure for submodules to be stepped
            if rel_path in SUBMODS_TO_STEP:
                continue

            # create directory structure for this module
            # Every module will be represented by a folder which will contain rst files for all its functions and
            # an rst file which will use all rst files in that folder to generate the overall markup
            new_filepath = (
                os.path.join("autogenerated_source", rel_path).replace(".py", "")
                + ".rst"
            )

            # Dotted namespace
            dotted_namespace = "/".join(
                module[repo_location:-3].split("/")[0 : i + 3]
            ).replace("/", ".")

            # title
            module_name = dotted_namespace.split(".")[-1]
            module_title = module_name.replace("_", " ")

            new_module_dir = os.path.join("autogenerated_source", rel_path).replace(
                ".py", ""
            )
            os.makedirs(new_module_dir, exist_ok=True)

            # writing the rst file for each module
            with open(new_filepath, "w+") as file:
                file.write(
                    (module_title).capitalize()
                    + "\n"
                    + "=" * len(module_title)
                    + "\n\n"
                    ".. automodule:: " + dotted_namespace + "\n"
                    "    :members:\n"
                    "    :special-members: __init__\n"
                    "    :undoc-members:\n"
                    "    :show-inheritance:\n"
                )

        # Get all function and class names in the module
        # The dotted namespace helps generate fully qualified class and function names
        functions, classes = get_functions_and_classes(module, dotted_namespace)

        # Extract function names from fully qualified names
        function_names = [item.split(".")[-1] for item in functions]

        # Extract class names from fully qualified names
        class_names = [item.split(".")[-1] for item in classes]

        # Add toctree for functions in module
        # For every function and class, a separate rst file is created and stored in the module dir
        toctree_dict = {
            module_name: [func_name + ".rst" for func_name in function_names]
            + [class_name + ".rst" for class_name in class_names]
        }
        append_toctree_to_rst(toctree_dict, new_filepath)

        # Update logo path for supported_frameworks
        supported_fw_str = SUPPORTED_FRAMEWORKS.replace(
            "logos", "../" * directory.count("/") + "logos"
        )

        # Write function rst files
        for func_name, dotted_func in zip(function_names, functions):
            function_filepath = os.path.join(new_module_dir, func_name) + ".rst"
            extension = ""
            if "array_methods" in function_filepath:
                extension = " array"
            elif "container_methods" in function_filepath:
                extension = " container"
            table = ""
            global IVY_ONLY
            if IVY_ONLY:
                flags, valid = get_flags(func_name)
                if valid:
                    table = DEVICE_SUPPORT_STR.format(*flags)
            with open(function_filepath, "w+") as file:
                file.write(
                    func_name
                    + extension
                    + "\n"
                    + "=" * len(func_name + extension)
                    + "\n\n"
                    ".. autofunction:: "
                    + dotted_func
                    + "\n"
                    + supported_fw_str
                )

        # Write class rst files
        for class_name, dotted_class in zip(class_names, classes):
            class_filepath = os.path.join(new_module_dir, class_name) + ".rst"
            with open(class_filepath, "w+") as file:
                file.write(
                    class_name + "\n" + "=" * len(class_name) + "\n\n"
                    ".. autoclass:: "
                    + dotted_class
                    + "\n"
                    + "   :members:\n"
                    + "   :special-members: __init__\n"
                    + "   :undoc-members:\n"
                    + "   :show-inheritance:\n"
                    + supported_fw_str
                )

    # README.rst is the main file which represents the overall folder for which documentation is generated
    if "README.rst" in contents or directory in [
        os.path.join(ROOT_DIR, sts) for sts in SUBMODS_TO_STEP
    ]:

        doc_save_dir_split = doc_save_dir.split("/")
        readme_save_dir = "/".join(doc_save_dir_split[:-1])
        module_name = doc_save_dir_split[-1]
        rst_filename = module_name + ".rst"
        readme_path = os.path.join(directory, "README.rst")
        rst_path = os.path.join(readme_save_dir, rst_filename)

        # Whenever a folder contains a README.rst file, we copy it to the autogenerated source as module_name.rst
        if "README.rst" in contents:
            copy_readme_to_rst(readme_path, rst_path)

        # append toctree
        # this contains all the rst file names generated
        toctree_key = module_name
        toctree_key_values = [item.split("/")[-1] + ".rst" for item in sub_dirs] + [
            item.split("/")[-1][:-3] + ".rst" for item in modules
        ]
        toctree_key_v_wo_rst = tuple(
            [tkv.replace(".rst", "") for tkv in toctree_key_values]
        )
        if toctree_key_v_wo_rst in SUBMOD_ORDERS:
            toctree_key_values = [
                so + ".rst" for so in SUBMOD_ORDERS[toctree_key_v_wo_rst]
            ]
        toctree_dict = {toctree_key: toctree_key_values}
        append_toctree_to_rst(toctree_dict, rst_path)

    # Used to create index.rst
    if directory == ROOT_DIR:
        if SUBMODULE_TITLE is not None:
            create_index_rst({"": modules})
        else:
            create_index_rst(sub_contents)

    return sub_dirs, modules


def append_instance_content_to_rst(
    function_type, path, files, file_str, functional_path
):
    functions = []
    for file in files:
        # Read array rst
        with open(os.path.join(path, file), "r") as f:
            rst_content = f.readlines()
            function_line = [
                line for line in rst_content if ".. autofunction::" in line
            ]
            if len(function_line) == 0:
                continue
            function_line = function_line[0]

        function_name = (function_line.strip("\n").split(" ")[2]).split(".")[-1]

        function_index = file_str.find("def {}(".format(function_name))
        submodule_index = file_str[0 : function_index + 1].rfind("#ivy.")
        submodule_name = (file_str[submodule_index:].split("\n")[0]).split(".")[-1]

        raw_function_name = str(function_name)
        if function_name.split("_")[0] == "static":
            function_name = "_".join(function_name.split("_")[1:])

        if submodule_name in ARRAY_CONTAINER_SUBMODULES_TO_SKIP:
            continue

        submodule_path = os.path.join(functional_path, submodule_name)

        if not os.path.exists(submodule_path):
            continue

        function_file = [
            file
            for file in os.listdir(submodule_path)
            if file == "{}.rst".format(function_name)
        ]

        if len(function_file) == 0:
            continue
        
        function_file = function_file[0]

        function_dir = os.path.join(submodule_path, function_name)
        os.makedirs(function_dir, exist_ok=True)

        with open(os.path.join(submodule_path, function_file)) as f:
            function_file_rst_content = f.readlines()
            submodule_function_line = [
                idx
                for idx in range(len(function_file_rst_content))
                if ".. autofunction::" in function_file_rst_content[idx]
            ][0]

        with open(
            os.path.join(function_dir, file[0:-4] + "_{}.rst".format(function_type)),
            "w",
        ) as f:
            for i in range(len(rst_content)):
                rst_content[i] = rst_content[i].replace("/logos", "/../../logos")
            rst_content[0] = "ivy.{}.{}\n".format(
                function_type.capitalize(), raw_function_name
            )
            rst_content[1] = "=" * len(rst_content[0].strip("\n"))
            f.writelines(rst_content)

        if not os.path.exists(
            os.path.join(function_dir, function_name + "_functional.rst")
        ):
            with open(
                os.path.join(function_dir, function_name + "_functional.rst"), "w"
            ) as f:
                temp_content = function_file_rst_content.copy()
                for i in range(len(temp_content)):
                    temp_content[i] = temp_content[i].replace("/logos", "/../logos")
                temp_content[0] = "ivy.{}\n".format(function_name)
                temp_content[1] = "=" * len(temp_content[0].strip("\n"))
                f.writelines(temp_content)

        final_content = (
            function_file_rst_content[0 : submodule_function_line + 1]
            + ["\n" + function_line]
            + function_file_rst_content[submodule_function_line + 1 :]
        )

        with open(os.path.join(submodule_path, function_file), "w") as f:
            f.writelines(final_content)

        functions.append(os.path.join(submodule_path, function_file))

    functions = list(set(functions))
    return functions


def add_instance_and_static_rsts():
    functional_path = os.path.join(
        THIS_DIR, "autogenerated_source", "functional", "ivy"
    )
    array_path = os.path.join(
        THIS_DIR, "autogenerated_source", "array", "array_methods"
    )
    array_code_path = os.path.join(ROOT_DIR, "array", "array_methods.py")
    container_path = os.path.join(
        THIS_DIR, "autogenerated_source", "container", "container_methods"
    )
    container_code_path = os.path.join(ROOT_DIR, "container", "container_methods.py")

    # Read array code
    with open(array_code_path, "r") as f:
        array_str = f.read()

    # Read container code
    with open(container_code_path, "r") as f:
        container_str = f.read()

    # List all rst files inside array_methods
    array_files = os.listdir(array_path)

    # List all rst files inside container_methods
    container_files = os.listdir(container_path)

    functions1 = append_instance_content_to_rst(
        "container", container_path, container_files, container_str, functional_path
    )

    functions2 = append_instance_content_to_rst(
        "array", array_path, array_files, array_str, functional_path
    )

    functions = functions1 + functions2
    functions = list(set(functions))
    for function in functions:
        function_dir = function[0:-4]
        files = os.listdir(function_dir)
        index = [index for index in range(len(files)) if "functional" in files[index]][
            0
        ]
        temp = files[0]
        files[0] = files[index]
        files[index] = temp
        files[1:] = sorted(files[1:])
        toctree_dict = dict()
        toctree_dict[function_dir.split("/")[-1]] = files
        append_toctree_to_rst(toctree_dict, function, function_dir.split("/")[-1])


def write_header_to_rst(file_path, title, module_name):
    with open(file_path, "w") as f:
        f.write(
            title.capitalize() + "\n" + "=" * len(title) + "\n\n"
            ".. automodule:: "
            + module_name
            + "\n"
            + "    :members:\n"
            + "    :special-members: __init__\n"
            + "    :undoc-members:\n"
            + "    :show-inheritance:\n"
        )


def copy_contents_and_update_path(file_path, copy_from_file, submodule):
    content = []
    with open(copy_from_file) as f:
        content = f.readlines()
    i, n = 0, len(content)
    while i < n:
        if ':hidden:' in content[i]:
            content = content[0:i+1] + [content[i].replace('hidden', 'titlesonly')] + content[i+1:]
            i += 1
            n += 1
        if '/' in content[i]:
            function_file = '/'.join(copy_from_file.split('/')[0:-1]) + '/' + content[i].strip(' ').strip('\n')
            with open(function_file) as f:
                function_content = f.readlines()
            with open(function_file, 'w+') as f:
                f.writelines(function_content[3:])
            content[i] = content[i].replace(submodule, '{}/{}'.format(submodule, submodule))
        i += 1
    with open(file_path, 'w') as f:
        f.writelines(content)


def write_header_and_toctree_to_rst(
    folder_path, file_path, title, module_name, submodule
):
    if 'data_classes/array.rst' in file_path:
        copy_from_file = file_path.replace('data_classes/array.rst', 'data_classes/array/array.rst')
        copy_contents_and_update_path(file_path, copy_from_file, submodule)
    elif 'data_classes/container.rst' in file_path:
        copy_from_file = file_path.replace('data_classes/container.rst', 'data_classes/container/container.rst')
        copy_contents_and_update_path(file_path, copy_from_file, submodule)
    else:
        write_header_to_rst(file_path, title, module_name)
    toctree_dict = {}
    files = [file for file in os.listdir(folder_path) if ".rst" in file and file.split('/')[-1] not in ["array.rst", "container.rst"]]
    files.sort()
    toctree_dict[submodule] = files
    append_toctree_to_rst(toctree_dict, file_path, title)


def update_image_paths(folder_path, old_path, new_path):
    folders = [folder for folder in os.listdir(folder_path) if ".rst" not in folder]
    if len(folders) == 0:
        files = [file for file in os.listdir(folder_path) if ".rst" in file]
        for file in files:
            content = ""
            with open(os.path.join(folder_path, file)) as f:
                content = f.read()
            content = content.replace(old_path, new_path)
            with open(os.path.join(folder_path, file), "w") as f:
                f.write(content)
    for folder in folders:
        update_image_paths(os.path.join(folder_path, folder), old_path, new_path)


def move_folders_to_classes():
    doc_path = os.path.join(THIS_DIR, "autogenerated_source")
    data_classes_path = os.path.join(doc_path, "data_classes")
    os.makedirs(data_classes_path, exist_ok=True)
    shutil.move(os.path.join(doc_path, "array"), data_classes_path)
    shutil.move(os.path.join(doc_path, "container"), data_classes_path)

    write_header_and_toctree_to_rst(
        os.path.join(doc_path, "stateful"),
        os.path.join(doc_path, "stateful.rst"),
        "Framework Classes",
        "ivy.stateful",
        "stateful",
    )

    write_header_and_toctree_to_rst(
        os.path.join(doc_path, "data_classes", "array"),
        os.path.join(doc_path, "data_classes", "array.rst"),
        "Array",
        "ivy.Array",
        "array",
    )

    write_header_and_toctree_to_rst(
        os.path.join(doc_path, "data_classes", "container"),
        os.path.join(doc_path, "data_classes", "container.rst"),
        "Container",
        "ivy.Container",
        "container",
    )

    write_header_and_toctree_to_rst(
        os.path.join(doc_path, "data_classes"),
        os.path.join(doc_path, "data_classes.rst"),
        "Data Classes",
        "ivy.data_classes",
        "data_classes",
    )

    with open(os.path.join(doc_path, "index.rst")) as f:
        index_page_content = f.readlines()

    result_content = []
    toctree_content = []
    inside_toctree = False
    for i in range(len(index_page_content)):
        line = index_page_content[i]
        if ".. toctree::" in line:
            toctree_content.append("")
            inside_toctree = True
        if not inside_toctree:
            result_content.append(line)
        else:
            toctree_content[-1] += line
    toctree_content = [
        content
        for content in toctree_content
        if ":caption: Array" not in content
        and ":caption: Container" not in content
        and ":caption: Stateful" not in content
    ]
    index = [
        index
        for index in range(len(toctree_content))
        if ":caption: Functions" in toctree_content[index]
    ][0]

    with open(os.path.join(doc_path, "index.rst"), "w") as f:
        f.writelines(result_content)
        f.writelines(toctree_content[0 : index + 1])

    toctree_dict = {}
    files = [
        file
        for file in os.listdir(os.path.join(doc_path, "data_classes"))
        if ".rst" in file
    ]
    toctree_dict["data_classes"] = files
    append_toctree_to_rst(
        toctree_dict, os.path.join(doc_path, "index.rst"), "Data Classes", False
    )

    toctree_dict = {}
    files = [
        file
        for file in os.listdir(os.path.join(doc_path, "stateful"))
        if ".rst" in file
    ]
    toctree_dict["stateful"] = files
    append_toctree_to_rst(
        toctree_dict, os.path.join(doc_path, "index.rst"), "Framework Classes", False
    )

    with open(os.path.join(doc_path, "index.rst"), "a") as f:
        f.writelines(toctree_content[index + 1 :])


def main(root_dir, submodules_title):
    # This directory contains all files in the repository along with the permitted_namespaces.json, submods_to_skip.txt and submods_to_step.txt files
    global THIS_DIR
    THIS_DIR = os.path.dirname(os.path.realpath(__file__))

    # This refers to the ivy directory (../ivy).
    global ROOT_DIR
    ROOT_DIR = root_dir

    # There are no submodules for which documentation is generated
    global SUBMODULE_TITLE
    SUBMODULE_TITLE = submodules_title

    # These are the submodules which need to be skipped altogether while documentation generation
    submods_to_skip_path = os.path.join(THIS_DIR, "submods_to_skip.txt")
    if os.path.exists(submods_to_skip_path):
        global SUBMODS_TO_SKIP
        with open(submods_to_skip_path, "r") as f:
            SUBMODS_TO_SKIP = [l.replace("\n", "") for l in f.readlines()[1:]]

    # These are the submodules to step into (skipping the directory from doc stack)
    # This means they won't have their own index page
    submods_to_step_path = os.path.join(THIS_DIR, "submods_to_step.txt")
    if os.path.exists(submods_to_step_path):
        global SUBMODS_TO_STEP
        with open(submods_to_step_path, "r") as f:
            SUBMODS_TO_STEP = [l.replace("\n", "") for l in f.readlines()[1:]]

    # These are the submodules to process irrespective of alphabetical order
    submod_orders_path = os.path.join(THIS_DIR, "submod_orders.txt")
    if os.path.exists(submod_orders_path):
        global SUBMOD_ORDERS
        with open(submod_orders_path, "r") as f:
            submod_orders = [
                l.replace("\n", "").replace(" ", "")[1:-1].split(",")
                for l in f.readlines()[1:]
            ]
        submod_orders_sorted = [tuple(sorted(so)) for so in submod_orders]
        SUBMOD_ORDERS = dict(zip(submod_orders_sorted, submod_orders))

    # Here the project title is Ivy
    project_title = string.capwords(root_dir.split("/")[-1].replace("_", " "))

    global IVY_ONLY
    if project_title.lower() == "ivy":
        IVY_ONLY = True

    # The cofiguration file is updated with the name of the project
    with open("partial_source/conf.py", "r") as conf_file:
        conf_contents = conf_file.read()
        conf_contents = conf_contents.replace(
            "project = 'Ivy'", "project = '{}'".format(project_title)
        )

    with open("partial_source/conf.py", "w") as conf_file:
        conf_file.write(conf_contents)

    # just to remove previously generated rst files
    if os.path.exists("autogenerated_source"):
        shutil.rmtree("autogenerated_source")

    # All images will be used in the documentation so they are copied to the build folder.
    shutil.copytree("partial_source/images", "build/_images")
    shutil.copytree("partial_source", "autogenerated_source")

    if IVY_ONLY:
        # To add all instance methods into another file.
        add_instance_and_static_methods(root_dir)

    # To create all rst files which contain the markup used by sphinx for generating the documentation.
    create_rst_files(root_dir)

    if IVY_ONLY:
        # Modify rst file paths to display functional, array and container methods in the same section
        add_instance_and_static_rsts()

        # Remove files and folders created for instance methods
        shutil.rmtree("autogenerated_source/container/container_methods")
        os.remove("autogenerated_source/container/container_methods.rst")
        shutil.rmtree("autogenerated_source/array/array_methods")
        os.remove("autogenerated_source/array/array_methods.rst")

        # Move the stateful, array and container folders inside the classes folder
        move_folders_to_classes()

        write_discussion_links()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root_dir",
        type=str,
        required=True,
        help="Root directory of the repository relaitve to current directory.",
    )
    parser.add_argument(
        "--submodules_title",
        type=str,
        help="The title for the combination of submodules."
        "Only valid when there are no submodule directories.",
    )
    parsed_args = parser.parse_args()
    main(parsed_args.root_dir, parsed_args.submodules_title)
    print("RST files created")