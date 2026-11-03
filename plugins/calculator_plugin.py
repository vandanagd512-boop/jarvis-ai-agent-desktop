"""Calculator extension plugin for JARVIS."""

from typing import Any, Dict, List
import math
from jarvis.plugins.base_plugin import BasePlugin, PluginTool


class CalculatorPlugin(BasePlugin):
    """Provides high-precision mathematical evaluation."""

    name = "CalculatorPlugin"
    version = "1.0.0"
    author = "JARVIS Team"
    description = "Evaluates mathematical calculations and expressions safely."

    def on_load(self) -> None:
        pass

    def on_unload(self) -> None:
        pass

    def calculate(self, expression: str) -> Dict[str, Any]:
        """Safely compute math expression."""
        allowed_names = {
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "sqrt": math.sqrt,
            "log": math.log,
            "pi": math.pi,
            "e": math.e,
            "pow": pow,
            "abs": abs,
            "round": round,
        }
        try:
            # Safe evaluation restricting builtins
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return {"success": True, "expression": expression, "result": result}
        except Exception as exc:
            return {"success": False, "expression": expression, "error": str(exc)}

    def get_tools(self) -> List[PluginTool]:
        return [
            PluginTool(
                name="calculate",
                description="Safely evaluate mathematical expressions like 'sqrt(144) + 25 * 4'.",
                handler=self.calculate,
            )
        ]
