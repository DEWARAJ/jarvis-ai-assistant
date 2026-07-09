"""Practical utility tools inspired by the sukeesh/jarvis toolkit.

All pure Python (stdlib only) — no external deps.
  - Unit conversion   : temperature, distance, weight, speed, time, data
  - BMI calculator    : weight + height -> BMI + category
  - Calorie calculator: BMR via Mifflin-St Jeor + activity multiplier
  - Password generator: cryptographically random (secrets module)
  - Safe math eval    : arithmetic + %, no exec
  - Joke library      : 30 built-in one-liners, no API
  - Translate         : routes to active LLM brain
"""
from __future__ import annotations
import ast, math, re, secrets, string

from tools.base_tool import BaseTool

# ---------------------------------------------------------------------------
# Unit conversion tables
# ---------------------------------------------------------------------------
_TEMP = {
    ("celsius", "fahrenheit"): lambda v: v * 9/5 + 32,
    ("fahrenheit", "celsius"): lambda v: (v - 32) * 5/9,
    ("celsius", "kelvin"):     lambda v: v + 273.15,
    ("kelvin", "celsius"):     lambda v: v - 273.15,
    ("fahrenheit", "kelvin"):  lambda v: (v - 32) * 5/9 + 273.15,
    ("kelvin", "fahrenheit"):  lambda v: (v - 273.15) * 9/5 + 32,
}

_UNITS: dict[str, float] = {
    # distance (base: metres)
    "km": 1000, "kilometer": 1000, "kilometres": 1000, "kilometers": 1000,
    "m": 1, "meter": 1, "metre": 1, "meters": 1, "metres": 1,
    "cm": 0.01, "centimeter": 0.01, "centimetre": 0.01, "centimeters": 0.01, "centimetres": 0.01,
    "mm": 0.001, "millimeter": 0.001, "millimetre": 0.001,
    "mile": 1609.344, "miles": 1609.344, "mi": 1609.344,
    "yard": 0.9144, "yards": 0.9144, "yd": 0.9144,
    "foot": 0.3048, "feet": 0.3048, "ft": 0.3048,
    "inch": 0.0254, "inches": 0.0254,
    "nautical mile": 1852, "nautical miles": 1852,
    # weight (base: kilograms)
    "kg": 1, "kilogram": 1, "kilograms": 1,
    "g": 0.001, "gram": 0.001, "grams": 0.001,
    "mg": 0.000001, "milligram": 0.000001, "milligrams": 0.000001,
    "lb": 0.453592, "lbs": 0.453592, "pound": 0.453592, "pounds": 0.453592,
    "oz": 0.0283495, "ounce": 0.0283495, "ounces": 0.0283495,
    "ton": 1000, "tonne": 1000, "tonnes": 1000, "tons": 1000,
    # speed (base: m/s)
    "m/s": 1, "mps": 1,
    "km/h": 1/3.6, "kph": 1/3.6,
    "mph": 0.44704,
    "knot": 0.514444, "knots": 0.514444,
    # time (base: seconds)
    "second": 1, "seconds": 1, "sec": 1,
    "minute": 60, "minutes": 60, "min": 60,
    "hour": 3600, "hours": 3600, "hr": 3600, "hrs": 3600,
    "day": 86400, "days": 86400,
    "week": 604800, "weeks": 604800,
    "month": 2592000, "months": 2592000,
    "year": 31536000, "years": 31536000,
    # data (base: bytes)
    "byte": 1, "bytes": 1,
    "kb": 1024, "kilobyte": 1024, "kilobytes": 1024,
    "mb": 1048576, "megabyte": 1048576, "megabytes": 1048576,
    "gb": 1073741824, "gigabyte": 1073741824, "gigabytes": 1073741824,
    "tb": 1099511627776, "terabyte": 1099511627776, "terabytes": 1099511627776,
}

_TEMP_ALIAS = {
    "c": "celsius", "f": "fahrenheit", "k": "kelvin",
    "°c": "celsius", "°f": "fahrenheit",
    "centigrade": "celsius",
}

_JOKES = [
    "Why don't scientists trust atoms? Because they make up everything, sir.",
    "I told my computer I needed a break. Now it won't stop sending me Kit-Kat ads.",
    "Why do programmers prefer dark mode? Because light attracts bugs, sir.",
    "A SQL query walks into a bar, walks up to two tables and asks: Can I join you?",
    "Why was the JavaScript developer sad? He didn't know how to null his feelings.",
    "I would tell you a UDP joke, but you might not get it.",
    "There are 10 types of people in the world: those who understand binary, and those who don't.",
    "Why do Java developers wear glasses? Because they don't C#.",
    "A programmer's wife says: go to the store, get a gallon of milk, and if they have eggs, get a dozen. He returns with 12 gallons of milk.",
    "Why did the developer quit his job? He didn't get arrays — sorry, a raise.",
    "How many programmers does it take to change a light bulb? None — that's a hardware problem.",
    "What's a computer's favourite snack? Microchips.",
    "I'm reading a book about anti-gravity. It's impossible to put down.",
    "Why did the physics teacher break up with the biology teacher? There was no chemistry.",
    "I asked my dog what two minus two is. He said nothing.",
    "Why don't eggs tell jokes? They'd crack each other up.",
    "I used to hate facial hair, but then it grew on me.",
    "What do you call a fake noodle? An impasta.",
    "Why did the scarecrow win an award? Because he was outstanding in his field.",
    "I'm on a seafood diet. Every time I see food, I eat it.",
    "Why can't you give Elsa a balloon? She'll let it go.",
    "I told my wife she should embrace her mistakes. She gave me a hug.",
    "Why did the bicycle fall over? Because it was two-tired.",
    "What do you call cheese that isn't yours? Nacho cheese.",
    "Why don't scientists trust stairs? Because they're always up to something.",
    "What do you call a sleeping dinosaur? A dino-snore.",
    "Did you hear about the mathematician afraid of negative numbers? He'll stop at nothing to avoid them.",
    "Why was the math book sad? It had too many problems.",
    "Why did the hipster burn his tongue? He drank his coffee before it was cool.",
    "I told my doctor I broke my arm in two places. He told me to stop going to those places.",
]


class UtilityTool(BaseTool):
    name = "utility"
    scope = "unit conversions, BMI, calories, password gen, safe math, jokes, translate"

    # ------------------------------------------------------------------ convert
    def convert(self, text: str) -> dict:
        """Parse 'convert <value> <from_unit> to <to_unit>'."""
        text_low = text.lower().strip()
        m = re.search(r"[-+]?\d*\.?\d+", text_low)
        if not m:
            return {"ok": False, "spoken": "I need a number to convert, sir. For example: convert 100 celsius to fahrenheit."}
        value = float(m.group())
        rest = text_low[m.end():].strip()
        if " to " not in rest:
            return {"ok": False, "spoken": "Please specify the target unit, sir. For example: convert 5 km to miles."}
        from_part, _, to_part = rest.partition(" to ")
        from_unit = from_part.strip()
        to_unit = to_part.strip()

        # temperature check
        fu = _TEMP_ALIAS.get(from_unit, from_unit)
        tu = _TEMP_ALIAS.get(to_unit, to_unit)
        if (fu, tu) in _TEMP:
            result = _TEMP[(fu, tu)](value)
            return {"ok": True, "spoken": f"{value} {fu} is {result:.2f} {tu}, sir."}

        # generic unit table
        from_factor = _UNITS.get(from_unit)
        to_factor = _UNITS.get(to_unit)
        if from_factor is None:
            return {"ok": False, "spoken": f"I don't recognise '{from_unit}' as a unit, sir. Try km, miles, kg, lbs, celsius, fahrenheit, hours, minutes, MB, GB, etc."}
        if to_factor is None:
            return {"ok": False, "spoken": f"I don't recognise '{to_unit}' as a unit, sir."}
        result = value * from_factor / to_factor
        result_str = str(int(result)) if result == int(result) else f"{result:.4g}"
        return {"ok": True, "spoken": f"{value} {from_unit} is {result_str} {to_unit}, sir."}

    # ------------------------------------------------------------------ bmi
    def bmi(self, text: str) -> dict:
        """Parse weight and height from free text and return BMI."""
        nums = re.findall(r"[-+]?\d*\.?\d+", text)
        if len(nums) < 2:
            return {"ok": False, "spoken": "I need weight and height, sir. For example: bmi 70 kg 175 cm."}
        weight_raw = float(nums[0])
        height_raw = float(nums[1])
        low = text.lower()
        # height conversion
        if "ft" in low or "feet" in low or "foot" in low:
            height_m = height_raw * 0.3048
            in_m = re.search(r"(\d+)\s*(?:in|inch)", low)
            if in_m:
                height_m += float(in_m.group(1)) * 0.0254
        elif "cm" in low or height_raw > 10:
            height_m = height_raw / 100
        else:
            height_m = height_raw
        # weight conversion
        weight_kg = weight_raw * 0.453592 if ("lb" in low or "pound" in low) else weight_raw
        if height_m <= 0:
            return {"ok": False, "spoken": "Height must be greater than zero, sir."}
        bmi_val = weight_kg / (height_m ** 2)
        if bmi_val < 18.5:
            cat = "underweight"
        elif bmi_val < 25:
            cat = "a healthy weight"
        elif bmi_val < 30:
            cat = "overweight"
        else:
            cat = "in the obese range"
        return {"ok": True, "spoken": (
            f"Your BMI is {bmi_val:.1f}, sir, which puts you in the {cat} category. "
            f"The healthy range is 18.5 to 24.9."
        )}

    # ------------------------------------------------------------------ calories
    def calories(self, text: str) -> dict:
        """Estimate daily calorie needs (Mifflin-St Jeor BMR x activity factor)."""
        nums = re.findall(r"\d+\.?\d*", text)
        low = text.lower()
        if len(nums) < 3:
            return {"ok": False, "spoken": (
                "I need age, weight, and height, sir. "
                "For example: calorie needs age 30 weight 75 kg height 175 cm male moderately active."
            )}
        age, weight_raw, height_raw = float(nums[0]), float(nums[1]), float(nums[2])
        height_cm = height_raw if ("cm" in low or height_raw > 10) else height_raw * 100
        weight_kg = weight_raw * 0.453592 if ("lb" in low or "pound" in low) else weight_raw
        male = "male" in low or " man" in low
        bmr = (10 * weight_kg + 6.25 * height_cm - 5 * age + 5) if male else (10 * weight_kg + 6.25 * height_cm - 5 * age - 161)
        if any(w in low for w in ("sedentary", "desk", "no exercise")):
            factor, label = 1.2, "sedentary"
        elif any(w in low for w in ("light", "lightly")):
            factor, label = 1.375, "lightly active"
        elif any(w in low for w in ("very active", "hard", "intense")):
            factor, label = 1.725, "very active"
        elif any(w in low for w in ("extremely", "athlete")):
            factor, label = 1.9, "extremely active"
        else:
            factor, label = 1.55, "moderately active"
        tdee = bmr * factor
        return {"ok": True, "spoken": (
            f"For a {'male' if male else 'female'} aged {int(age)}, {weight_kg:.0f} kg, {height_cm:.0f} cm, "
            f"{label}: estimated daily calories are {tdee:.0f}, sir. Basal rate is {bmr:.0f}."
        )}

    # ------------------------------------------------------------------ password
    def password(self, text: str) -> dict:
        """Generate a cryptographically secure password."""
        m = re.search(r"\d+", text)
        length = max(8, min(128, int(m.group()) if m else 16))
        low = text.lower()
        if any(w in low for w in ("simple", "easy", "memorable", "word")):
            words = ["alpha", "brave", "cloud", "delta", "echo", "forge", "gamma", "hunter",
                     "iron", "jade", "karma", "lance", "matrix", "nexus", "omega", "pulse",
                     "quartz", "raven", "sigma", "titan", "ultra", "vortex", "wolf", "xenon",
                     "yield", "zephyr", "amber", "blaze", "crisp", "dusk"]
            pw = "-".join(secrets.choice(words) for _ in range(4))
            return {"ok": True, "spoken": f"Memorable password, sir: {pw}"}
        no_sym = any(w in low for w in ("no symbol", "no special", "alphanumeric"))
        alphabet = string.ascii_letters + string.digits + ("" if no_sym else "!@#$%^&*()-_=+[]")
        pw = list(secrets.choice(alphabet) for _ in range(length))
        pw[0] = secrets.choice(string.ascii_uppercase)
        pw[1] = secrets.choice(string.ascii_lowercase)
        pw[2] = secrets.choice(string.digits)
        if not no_sym:
            pw[3] = secrets.choice("!@#$%^&*")
        secrets.SystemRandom().shuffle(pw)
        return {"ok": True, "spoken": f"Your {length}-character password, sir: {''.join(pw)}"}

    # ------------------------------------------------------------------ calculate
    def calculate(self, text: str) -> dict:
        """Safe arithmetic evaluator — whitelist AST only."""
        expr = re.sub(r"^(calculate|compute|what is|what's|evaluate|solve|calc|math)\s*", "", text.strip(), flags=re.I).rstrip("?. ")
        # "15% of 200" -> 15/100*200
        expr = re.sub(r"(\d+\.?\d*)\s*%\s*of\s*(\d+\.?\d*)",
                      lambda mm: str(float(mm.group(1)) / 100 * float(mm.group(2))), expr)
        expr = expr.replace("^", "**")
        # substitute pi/e before stripping non-numeric
        expr = re.sub(r"\bpi\b", str(math.pi), expr)
        expr = re.sub(r"\be\b", str(math.e), expr)
        expr_safe = re.sub(r"[^0-9+\-*/().\s*]", "", expr).strip()
        if not expr_safe:
            return {"ok": False, "spoken": f"I couldn't parse that as arithmetic, sir."}
        try:
            tree = ast.parse(expr_safe, mode="eval")
            allowed = {ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
                       ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
                       ast.FloorDiv, ast.USub, ast.UAdd}
            for node in ast.walk(tree):
                if type(node) not in allowed:
                    return {"ok": False, "spoken": "I can only evaluate arithmetic expressions, sir."}
            result = eval(compile(tree, "<string>", "eval"))  # noqa: S307 — AST-validated above
            result_str = str(int(result)) if isinstance(result, float) and result == int(result) else str(result)
            return {"ok": True, "spoken": f"{expr.strip()} = {result_str}, sir."}
        except ZeroDivisionError:
            return {"ok": False, "spoken": "Division by zero, sir. That's undefined."}
        except Exception as e:
            return {"ok": False, "spoken": f"I couldn't evaluate that, sir ({e})."}

    # ------------------------------------------------------------------ joke
    def joke(self) -> dict:
        return {"ok": True, "spoken": secrets.choice(_JOKES)}

    # ------------------------------------------------------------------ translate
    def translate(self, text: str, llm=None) -> dict:
        """Route translation request to the active LLM brain."""
        if llm is None:
            return {"ok": False, "spoken": "Translation requires the LLM brain to be online, sir."}
        m = re.search(r"\bto\s+([a-zA-Z]+)", text, re.I)
        lang = m.group(1) if m else "English"
        content = re.sub(r"^(translate|translation)\s*", "", text.strip(), flags=re.I)
        content = re.sub(r"\bto\s+[a-zA-Z]+\s*", "", content, flags=re.I).strip().strip(":").strip()
        if not content:
            return {"ok": False, "spoken": "What would you like me to translate, sir?"}
        prompt = f"Translate the following text to {lang}. Return ONLY the translation, no explanation:\n\n{content}"
        try:
            result = llm.chat(prompt, system="You are a professional translator. Return only the translation.")
            return {"ok": True, "spoken": f"Translation to {lang}, sir: {result}"}
        except Exception as e:
            return {"ok": False, "spoken": f"Translation failed, sir ({e})."}
