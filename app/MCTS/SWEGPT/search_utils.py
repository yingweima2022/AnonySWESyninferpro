import ast
import glob
import re
from os.path import join as pjoin
from typing import List, Optional, Tuple


def get_all_py_files(dir_path: str) -> List[str]:
    """Get all .py files recursively from a directory.

    Skips files that are obviously not from the source code, such third-party library code.

    Args:
        dir_path (str): Path to the directory.
    Returns:
        List[str]: List of .py file paths. These paths are ABSOLUTE path!
    """

    py_files = glob.glob(pjoin(dir_path, "**/*.py"), recursive=True)
    res = []
    for file in py_files:
        rel_path = file[len(dir_path) + 1:]
        if rel_path.startswith("build"):
            continue
        if rel_path.startswith("doc"):
            # discovered this issue in 'pytest-dev__pytest'
            continue
        if rel_path.startswith("requests/packages"):
            # to walkaround issue in 'psf__requests'
            continue
        if (
            rel_path.startswith("tests/regrtest_data")
            or rel_path.startswith("tests/input")
            or rel_path.startswith("tests/functional")
        ):
            # to walkaround issue in 'pylint-dev__pylint'
            continue
        if rel_path.startswith("tests/roots") or rel_path.startswith(
            "sphinx/templates/latex"
        ):
            # to walkaround issue in 'sphinx-doc__sphinx'
            continue
        if rel_path.startswith("tests/test_runner_apps/tagged/") or rel_path.startswith(
            "django/conf/app_template/"
        ):
            # to walkaround issue in 'django__django'
            continue
        if "pytest" not in file:
            # 如果不是pytest类库
            if rel_path.startswith("test"):
                continue
        res.append(file)
    return res


def get_all_classes_in_file(file_full_path: str) -> List[Tuple[str, int, int]]:
    """Get all classes defined in one .py file.

    Args:
        file_path (str): Path to the .py file.
    Returns:
        List of classes in this file.
    """

    with open(file_full_path, "r") as f:
        file_content = f.read()

    classes = []
    # print(file_path)
    tree = ast.parse(file_content)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_name = node.name
            start_lineno = node.lineno
            end_lineno = node.end_lineno
            # line numbers are 1-based
            classes.append((class_name, start_lineno, end_lineno))
    return classes


def get_all_functions_in_file(file_full_path: str) -> List[Tuple[str, int, int]]:
    """Get all functions defined in one .py file.

    Args:
        file_path (str): Path to the .py file.
    Returns:
        List of functions in this file.
    """
    functions = []
    top_level_functions = get_top_level_functions(file_full_path)
    functions.extend(top_level_functions)

    classes = get_all_classes_in_file(file_full_path)

    for class_name, start_lineno, end_lineno in classes:
        class_functions = get_all_funcs_in_class_in_file(file_full_path, class_name)
        functions.extend(class_functions)

    return functions


def get_top_level_functions(file_full_path: str) -> List[Tuple[str, int, int]]:
    """Get top-level functions defined in one .py file.

    This excludes functions defined in any classes.

    Args:
        file_path (str): Path to the .py file.
    Returns:
        List of top-level functions in this file.
    """
    with open(file_full_path, "r") as f:
        file_content = f.read()

    functions = []
    tree = ast.parse(file_content)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_name = node.name
            start_lineno = node.lineno
            end_lineno = node.end_lineno
            # line numbers are 1-based
            functions.append((function_name, start_lineno, end_lineno))
    return functions


# mainly used for building index
def get_all_funcs_in_class_in_file(
    file_full_path: str, class_name: str
) -> List[Tuple[str, int, int]]:
    """
    For a class in a file, get all functions defined in the class.
    Assumption:
        - the given function exists, and is defined in the given file.
    Returns:
        - List of tuples, each tuple is (function_name, start_lineno, end_lineno).
    """
    with open(file_full_path, "r") as f:
        file_content = f.read()

    functions = []
    tree = ast.parse(file_content)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for n in ast.walk(node):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    function_name = n.name
                    start_lineno = n.lineno
                    end_lineno = n.end_lineno
                    functions.append((function_name, start_lineno, end_lineno))

    return functions


def get_func_snippet_in_class(
    file_full_path: str, class_name: str, func_name: str, include_lineno=False
) -> Optional[str]:
    """Get actual function source code in class.

    All source code of the function is returned.
    Assumption: the class and function exist.
    """
    with open(file_full_path, "r") as f:
        file_content = f.read()

    tree = ast.parse(file_content)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for n in ast.walk(node):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == func_name:
                    start_lineno = n.lineno
                    end_lineno = n.end_lineno
                    assert end_lineno is not None, "end_lineno is None"
                    if include_lineno:
                        return get_code_snippets_with_lineno(
                            file_full_path, start_lineno, end_lineno
                        )
                    else:
                        return get_code_snippets(
                            file_full_path, start_lineno, end_lineno
                        )
    # In this file, cannot find either the class, or a function within the class
    return None


def get_code_region_containing_code(
    file_full_path: str, code_str: str
) -> List[Tuple[int, str]]:
    """In a file, get the region of code that contains a specific string.

    Args:
        - file_full_path: Path to the file. (absolute path)
        - code_str: The string that the function should contain.
    Returns:
        - A list of tuple, each of them is a pair of (line_no, code_snippet).
        line_no is the starting line of the matched code; code snippet is the
        source code of the searched region.
    """
    with open(file_full_path, "r") as f:
        file_content = f.read()

    context_size = 3
    # since the code_str may contain multiple lines, let's not split the source file.

    # we want a few lines before and after the matched string. Since the matched string
    # can also contain new lines, this is a bit trickier.
    pattern = re.compile(re.escape(code_str))
    # each occurrence is a tuple of (line_no, code_snippet) (1-based line number)
    occurrences: List[Tuple[int, str]] = []
    for match in pattern.finditer(file_content):
        matched_start_pos = match.start()
        # first, find the line number of the matched start position (1-based)
        matched_line_no = file_content.count("\n", 0, matched_start_pos) + 1
        # next, get a few surrounding lines as context
        search_start = match.start() - 1
        search_end = match.end() + 1
        # from the matched position, go left to find 5 new lines.
        for _ in range(context_size):
            # find the \n to the left
            left_newline = file_content.rfind("\n", 0, search_start)
            if left_newline == -1:
                # no more new line to the left
                search_start = 0
                break
            else:
                search_start = left_newline
        # go right to fine 5 new lines
        for _ in range(context_size):
            right_newline = file_content.find("\n", search_end + 1)
            if right_newline == -1:
                # no more new line to the right
                search_end = len(file_content)
                break
            else:
                search_end = right_newline

        start = max(0, search_start)
        end = min(len(file_content), search_end)
        context = file_content[start:end]
        occurrences.append((matched_line_no, context))

    return occurrences


def get_func_snippet_with_code_in_file(file_full_path: str, code_str: str) -> List[str]:
    """In a file, get the function code, for which the function contains a specific string.

    Args:
        file_full_path (str): Path to the file. (absolute path)
        code_str (str): The string that the function should contain.

    Returns:
        A list of code snippets, each of them is the source code of the searched function.
    """
    with open(file_full_path, "r") as f:
        file_content = f.read()

    tree = ast.parse(file_content)
    all_snippets = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        func_start_lineno = node.lineno
        func_end_lineno = node.end_lineno
        assert func_end_lineno is not None
        func_code = get_code_snippets(
            file_full_path, func_start_lineno, func_end_lineno
        )
        # This func code is a raw concatenation of source lines which contains new lines and tabs.
        # For the purpose of searching, we remove all spaces and new lines in the code and the
        # search string, to avoid non-match due to difference in formatting.
        stripped_func = " ".join(func_code.split())
        stripped_code_str = " ".join(code_str.split())
        if stripped_code_str in stripped_func:
            all_snippets.append(func_code)

    return all_snippets


def get_code_snippets_with_lineno(file_full_path: str, start: int, end: int) -> str:
    """Get the code snippet in the range in the file.

    The code snippet should come with line number at the beginning for each line.

    TODO: When there are too many lines, return only parts of the output.
          For class, this should only involve the signatures.
          For functions, maybe do slicing with dependency analysis?

    Args:
        file_path (str): Path to the file.
        start (int): Start line number. (1-based)
        end (int): End line number. (1-based)
    """
    with open(file_full_path, "r") as f:
        file_content = f.readlines()

    snippet = ""
    for i in range(start - 1, end):
        snippet += f"{i+1} {file_content[i]}"
    return snippet


def get_code_snippets(file_full_path: str, start: int, end: int) -> str:
    """Get the code snippet in the range in the file, without line numbers.

    Args:
        file_path (str): Full path to the file.
        start (int): Start line number. (1-based)
        end (int): End line number. (1-based)
    """
    with open(file_full_path, "r") as f:
        file_content = f.readlines()
    snippet = ""
    for i in range(start - 1, end):
        snippet += file_content[i]
    return snippet


def extract_func_sig_from_ast(func_ast: ast.FunctionDef) -> List[int]:
    """Extract the function signature from the AST node.

    Includes the decorators, method name, and parameters.

    Args:
        func_ast (ast.FunctionDef): AST of the function.

    Returns:
        The source line numbers that contains the function signature.
    """
    func_start_line = func_ast.lineno
    if func_ast.decorator_list:
        # has decorators
        decorator_start_lines = [d.lineno for d in func_ast.decorator_list]
        decorator_first_line = min(decorator_start_lines)
        func_start_line = min(decorator_first_line, func_start_line)
    # decide end line from body
    if func_ast.body:
        # has body
        body_start_line = func_ast.body[0].lineno
        end_line = body_start_line - 1
    else:
        # no body
        end_line = func_ast.end_lineno
    assert end_line is not None
    return list(range(func_start_line, end_line + 1))


def extract_class_sig_from_ast(class_ast: ast.ClassDef) -> List[int]:
    """Extract the class signature from the AST.

    Args:
        class_ast (ast.ClassDef): AST of the class.

    Returns:
        The source line numbers that contains the class signature.
    """
    # STEP (1): extract the class signature
    sig_start_line = class_ast.lineno
    if class_ast.body:
        # has body
        body_start_line = class_ast.body[0].lineno
        sig_end_line = body_start_line - 1
    else:
        # no body
        sig_end_line = class_ast.end_lineno
    assert sig_end_line is not None
    sig_lines = list(range(sig_start_line, sig_end_line + 1))

    # STEP (2): extract the function signatures and assign signatures
    for stmt in class_ast.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sig_lines.extend(extract_func_sig_from_ast(stmt))
        elif isinstance(stmt, ast.Assign):
            # for Assign, skip some useless cases where the assignment is to create docs
            stmt_str_format = ast.dump(stmt)
            if "__doc__" in stmt_str_format:
                continue
            # otherwise, Assign is easy to handle
            assert stmt.end_lineno is not None
            assign_range = list(range(stmt.lineno, stmt.end_lineno + 1))
            sig_lines.extend(assign_range)

    return sig_lines


def extract_class_sig_from_ast_with_comments(class_ast: ast.ClassDef) -> List[int]:
    """Extract the class signature from the AST.

    Args:
        class_ast (ast.ClassDef): AST of the class.

    Returns:
        The source line numbers that contains the class signature.
    """
    # STEP (1): extract the class signature
    sig_start_line = class_ast.lineno
    if class_ast.body:
        # has body
        body_start_line = class_ast.body[0].lineno
        sig_end_line = body_start_line - 1
    else:
        # no body
        sig_end_line = class_ast.end_lineno
    assert sig_end_line is not None
    sig_lines = list(range(sig_start_line, sig_end_line + 1))

    # STEP (1.5): add docstring
    if ast.get_docstring(class_ast):
        docstring_node = ast.get_docstring(class_ast, clean=False)
        doc_lines = docstring_node.split("\n")
        if doc_lines:
            doc_start_line = sig_start_line + 1  # Assuming docstring starts right after the class definition line
            doc_end_line = doc_start_line + len(doc_lines) - 1
            sig_lines.extend(range(doc_start_line, doc_end_line + 1))

    # STEP (2): extract the function signatures and assign signatures
    for stmt in class_ast.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sig_lines.extend(extract_func_sig_from_ast(stmt))
        elif isinstance(stmt, ast.Assign):
            # for Assign, skip some useless cases where the assignment is to create docs
            stmt_str_format = ast.dump(stmt)
            if "__doc__" in stmt_str_format:
                continue
            # otherwise, Assign is easy to handle
            assert stmt.end_lineno is not None
            assign_range = list(range(stmt.lineno, stmt.end_lineno + 1))
            sig_lines.extend(assign_range)

    return sig_lines


def get_class_signature(file_full_path: str, class_name: str) -> str:
    """Get the class signature.

    Args:
        file_path (str): Path to the file.
        class_name (str): Name of the class.
    """
    with open(file_full_path, "r") as f:
        file_content = f.read()

    tree = ast.parse(file_content)
    relevant_lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            # we reached the target class
            relevant_lines = extract_class_sig_from_ast_with_comments(node)
            break
    if not relevant_lines:
        return ""
    else:
        with open(file_full_path, "r") as f:
            file_content = f.readlines()
        result = ""
        for line in relevant_lines:
            line_content: str = file_content[line - 1]
            if line_content.strip().startswith("#"):
                # this kind of comment could be left until this stage.
                # reason: # comments are not part of func body if they appear at beginning of func
                continue
            result += line_content
        return result


def get_class_content(file_full_path: str, class_start_line, class_end_line) -> str:
    content = get_code_snippets(file_full_path, class_start_line, class_end_line)
    return content


def get_global_variables_corrected(file_full_path: str) -> List[Tuple[str, int, int]]:
    """
    Extract all global variables defined at the top level in a .py file.

    Args:
        file_full_path (str): Path to the .py file.

    Returns:
        List of tuples, each containing:
        (variable_name, start_lineno, end_lineno, # value_as_code)
    """
    with open(file_full_path, "r") as f:
        file_content = f.read()

    tree = ast.parse(file_content)
    global_vars = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            # An assignment at the top level is considered a global variable
            for target in node.targets:
                if isinstance(target, ast.Name):
                    start_lineno = node.lineno
                    end_lineno = getattr(node, 'end_lineno', start_lineno)  # end_lineno is available in Python 3.8+
                    # Extracting the value as a string of code
                    value_code = ast.unparse(node.value)
                    global_vars.append((target.id, start_lineno, end_lineno))
        elif isinstance(node, ast.AnnAssign):
            # Handle annotated assignments
            if isinstance(node.target, ast.Name):
                start_lineno = node.lineno
                end_lineno = getattr(node, 'end_lineno', start_lineno)
                value_code = ast.unparse(node.value) if node.value is not None else 'None'
                global_vars.append((node.target.id, start_lineno, end_lineno))

    return global_vars

