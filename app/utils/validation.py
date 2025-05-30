import json

def recursive_grep(data, search_strings, current_path=[], matches=None):
    """
    Recursively searches for strings within a nested data structure (dicts and lists).

    Args:
        data: The current data structure (dict, list, or other value) to search.
        search_strings (list): A list of strings to search for.
        current_path (list): The path (keys/indices) to the current data element.
        matches (list): A list to store the paths where the search strings are found.
                        If None, a new list is created.

    Returns:
        list: A list of paths (as lists of keys/indices) where any of the search strings were found.
    """
    if matches is None:
        matches = []

    if isinstance(data, dict):
        for key, value in data.items():
            recursive_grep(value, search_strings, current_path + [key], matches)
    elif isinstance(data, list):
        for index, item in enumerate(data):
            recursive_grep(item, search_strings, current_path + [index], matches)
    else:
        # Convert non-string values to string for consistent searching
        if not isinstance(data, str):
            data = str(data)

        if any(search_string in data for search_string in search_strings):
            matches.append(current_path)

    return matches

def get_context_data(data, path, level):
    """
    Retrieves data from the original data structure based on a given path and context level.

    Args:
        data: The original data structure.
        path (list): The path (list of keys/indices) to the matched element.
        level (int): The hierarchical level of context to return.

    Returns:
        The data at the specified context level.
    """
    context_path = path[:len(path) - level]
    current_data = data
    try:
        for step in context_path:
            current_data = current_data[step]
        return current_data
    except (KeyError, IndexError):
        return None # Should not happen if path is valid


def grep_json_hierarchical(data_input, search_strings, level=2):
    """
    Searches for strings within a JSON formatted string or a Python dictionary
    and prints hierarchical context around the matches. Can search for a single
    string or a list of strings.

    Args:
        data_input (str or dict): The JSON formatted string or Python dictionary
                                 to search within.
        search_strings (str or list): The string or a list of strings to search for.
        level (int): The hierarchical level of context to print (0 for the value itself,
                     1 for its parent, 2 for the grandparent, etc.).
    """
    data = None
    if isinstance(data_input, str):
        try:
            data = json.loads(data_input)
        except json.JSONDecodeError:
            print("Error: Input string is not valid JSON.")
            return
    elif isinstance(data_input, dict):
        data = data_input
    else:
        print("Error: Input must be a JSON formatted string or a Python dictionary.")
        return

    # Ensure search_strings is a list
    if isinstance(search_strings, str):
        search_list = [search_strings]
    elif isinstance(search_strings, list):
        search_list = search_strings
    else:
        print("Error: search_strings must be a string or a list of strings.")
        return

    # Initialize matches here before calling recursive_grep
    matches = []
    recursive_grep(data, search_list, matches=matches) # Pass the initialized matches list

    if not matches:
        if len(search_list) == 1:
            print(f"'{search_list[0]}' not found in the data.")
        else:
            print(f"None of the search strings found in the data.")
        return

    print(f"Found matches for {search_list} in the following locations (context level: {level}):")
    printed_context_data = set() # Use a set to store string representations of context data to avoid duplicates

    for match_path in matches:
        context_data = get_context_data(data, match_path, level)

        if context_data is not None:
             # Convert the context data to a string representation for the set
            # Handle cases where context_data is not JSON serializable by trying to represent it as a string
            try:
                context_data_str = json.dumps(context_data, sort_keys=True)
            except TypeError:
                context_data_str = str(context_data)

            if context_data_str not in printed_context_data:
                print("-" * 20)
                # Attempt to print as JSON, fallback to string if not serializable
                try:
                    print(json.dumps(context_data, indent=2))
                except TypeError:
                    print(context_data)
                printed_context_data.add(context_data_str)
        else:
             print(f"Could not retrieve context for path: {match_path}")