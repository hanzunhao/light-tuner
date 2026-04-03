"""
Code Parameter Injection Utility Module
Provides functionality to convert dictionaries to Python strings and replace
parameter dictionaries within source code using AST manipulation.
"""
import ast
from typing import Dict, Any
from light_tuner.utils.logger import logger


def convert_dict_to_python_str(parameters: Dict[Any, Any]) -> str:
    """
    Converts a dictionary into a valid Python dictionary string representation.
    """
    # Validate input type
    if not isinstance(parameters, dict):
        error_msg = f"Dictionary conversion failed: Input must be a dict, got {type(parameters)}."
        logger.error(error_msg)
        raise TypeError(error_msg)

    return repr(parameters)


def replace_parameter_dict_in_code(
        code_content: str,
        target_dict_name: str,
        new_parameter_dict: Dict[Any, Any]
) -> str:
    """
    Injects a new parameter dictionary into the source code by finding and
    replacing a specific variable assignment using Abstract Syntax Trees (AST).

    Args:
        code_content: The original Python source code string.
        target_dict_name: The name of the dictionary variable to be replaced.
        new_parameter_dict: The dictionary containing the new hyperparameter values.

    Returns:
        str: The modified source code with the injected parameters.
    """
    if not code_content:
        logger.error("Code injection failed: Original code content is empty.")
        raise ValueError("code_content cannot be an empty string.")

    if not target_dict_name:
        logger.error("Code injection failed: Target dictionary variable name cannot be empty.")
        raise ValueError("target_dict_name cannot be an empty string.")

    if not isinstance(new_parameter_dict, dict):
        error_type = type(new_parameter_dict)
        logger.error(f"Code injection failed: New parameter dict must be a dict type, got {error_type}.")
        raise TypeError(f"New parameter dict must be a dict type, got {error_type}.")

    try:
        # Parse the source code into an AST
        tree = ast.parse(code_content)
        replaced = False

        # Create a new AST node from the new dictionary
        # ast.parse returns a Module; we extract the value from the first expression
        new_dict_node = ast.parse(convert_dict_to_python_str(new_parameter_dict)).body[0].value

        # Walk through the tree to find the target assignment
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == target_dict_name:
                        # Perform replacement: Replace the old right-hand side with the new node
                        node.value = new_dict_node
                        replaced = True

        if not replaced:
            logger.warning(f"Could not find a replaceable dictionary variable named '{target_dict_name}' in the code.")
            return code_content

        # Unparse the modified AST back into source code string
        return ast.unparse(tree)

    except SyntaxError as se:
        logger.error(f"Code injection failed due to syntax errors in source: {se}")
        return code_content
    except Exception as e:
        logger.error(f"An unexpected error occurred during AST processing: {e}")
        return code_content