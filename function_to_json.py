from tools.scan_windows_temp_files import scan_windows_temp_files
import inspect

def function_to_json(func):
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        type(None): "null",
    }
    # 获取函数签名如果失败则返回函数名和错误
    try:
        signature = inspect.signature(func)
    except ValueError as e:
        raise ValueError(f"Failed to get signature for function {func.__name__}: {str(e)}")

    parameters = {}
    for param in signature.parameters.values():
        try:
            param_type = type_map.get(param.annotation, "string")
        except KeyError:
            raise ValueError(f"Failed to get type for parameter {param.name}")
        
        parameters[param.name] = {
            "type": param_type
        }

    required = [
        param.name
        for param in signature.parameters.values()
        if param.default == inspect._empty
    ]

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": func.__doc__ or "",
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required,
            },
        },
    }

if __name__ == "__main__":
    print(function_to_json(scan_windows_temp_files))
