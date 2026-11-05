import ast
import html
import random
import re
from dataclasses import dataclass

import streamlit as st


st.set_page_config(page_title="Equation Balance Lab", page_icon="⚖️", layout="wide")


@dataclass(frozen=True)
class Linear:
    x: float = 0
    c: float = 0

    def __add__(self, other):
        return Linear(self.x + other.x, self.c + other.c)

    def __neg__(self):
        return Linear(-self.x, -self.c)

    def __sub__(self, other):
        return self + -other

    def times(self, k):
        return Linear(self.x * k, self.c * k)

    def close(self, other):
        return abs(self.x - other.x) < 1e-7 and abs(self.c - other.c) < 1e-7


def parse_linear(text):
    """Parse a safe, restricted linear expression. Never eval student input."""
    source = str(text).strip().replace("−", "-").replace("×", "*").replace("÷", "/")
    source = re.sub(r"(\d|\))\s*(x|\()", r"\1*\2", source, flags=re.I)
    source = re.sub(r"(x|\))\s*\(", r"\1*(", source, flags=re.I)
    source = re.sub(r"\)\s*(\d)", r")*\1", source)
    tree = ast.parse(source, mode="eval")

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Name) and node.id.lower() == "x":
            return Linear(1, 0)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return Linear(0, float(node.value))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -walk(node.operand)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
            return walk(node.operand)
        if isinstance(node, ast.BinOp):
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                if abs(left.x) > 1e-9 and abs(right.x) > 1e-9:
                    raise ValueError("Only linear expressions are supported.")
                return Linear(left.x * right.c + left.c * right.x, left.c * right.c)
            if isinstance(node.op, ast.Div):
                if abs(right.x) > 1e-9 or abs(right.c) < 1e-9:
                    raise ValueError("Divide only by a nonzero number.")
                return left.times(1 / right.c)
        raise ValueError("Use numbers, x, +, −, ×, ÷ and parentheses.")

    return walk(tree)


def num(value):
    if abs(value) < 1e-9:
        return "0"
    if abs(value - round(value)) < 1e-9:
        return str(round(value))
    return f"{value:.5g}"


def expression(value):
    items = []
    if abs(value.x) > 1e-9:
        if abs(value.x - 1) < 1e-9:
            items.append("x")
        elif abs(value.x + 1) < 1e-9:
            items.append("-x")
        else:
            items.append(f"{num(value.x)}x")
    if abs(value.c) > 1e-9:
        if not items:
            items.append(num(value.c))
        elif value.c < 0:
            items.append(f"− {num(abs(value.c))}")
        else:
            items.append(f"+ {num(value.c)}")
    return " ".join(items) if items else "0"


def equation(left, right):
    return f"{expression(left)} = {expression(right)}"



def substituted_equation(original, value):
    """Display substitution in the original, unsimplified equation."""
    replacement = f"({num(value)})"
    # Match the variable x, including when attached to a coefficient like 3x.
    # Put the value in parentheses to preserve negative signs.
    return re.sub(r"x", lambda _: replacement, original, flags=re.I)


def show_solution_check(problem, original, value):
    """Show the original equation, substitution, and evaluated sides."""
    substituted = substituted_equation(original, value)
    left_result = problem["left"].x * value + problem["left"].c
    right_result = problem["right"].x * value + problem["right"].c

    st.markdown("#### Check your solution")
    st.caption("Replace x in the ORIGINAL equation, then simplify each side.")
    with st.container(border=True):
        st.markdown("**1. Original equation**")
        st.markdown(f'<div class="check-math">{html.escape(original)}</div>',
                    unsafe_allow_html=True)
        st.markdown(f"**2. Substitute x = {num(value)}**")
        st.markdown(f'<div class="check-math">{html.escape(substituted)}</div>',
                    unsafe_allow_html=True)
        st.markdown("**3. Simplify both sides**")
        st.markdown(f'<div class="check-math">{num(left_result)} = {num(right_result)}</div>',
                    unsafe_allow_html=True)
        if abs(left_result - right_result) < 1e-7:
            st.success("Both sides are equal. The solution checks!")
        else:
            st.error("The two sides do not match. Recheck the solution.")

def make_problem(level):
    solution = random.choice([n for n in range(-9, 13) if n != 0])
    if level == 1:
        kind = random.choice(["add", "subtract", "multiply", "divide"])
        if kind in ("add", "subtract"):
            amount = random.randint(2, 12)
            b = amount if kind == "add" else -amount
            left = Linear(1, b)
            right = Linear(0, solution + b)
        elif kind == "multiply":
            a = random.choice([-5, -3, -2, 2, 3, 4, 5])
            left = Linear(a, 0)
            right = Linear(0, a * solution)
        else:
            divisor = random.choice([2, 3, 4, 5])
            left = Linear(1 / divisor, 0)
            right = Linear(0, solution / divisor)
        return {"left": left, "right": right, "display": None, "solution": solution, "simplify": False}
    if level == 2:
        a = random.choice([-5, -3, -2, 2, 3, 4, 5])
        b = random.choice([-11, -8, -5, 4, 6, 9, 12])
        left = Linear(a, b)
        right = Linear(0, a * solution + b)
        return {"left": left, "right": right, "display": None, "solution": solution, "simplify": False}
    kind = random.choice(["variable", "distribute", "combine"])
    if kind == "variable":
        right_a = random.choice([1, 2, 3])
        difference = random.choice([2, 3, 4, 5])
        left_a = right_a + difference
        left_b = random.randint(-9, 9)
        right_b = difference * solution + left_b
        left, right = Linear(left_a, left_b), Linear(right_a, right_b)
        display = None
        simplify = False
    elif kind == "distribute":
        factor = random.choice([2, 3, 4])
        inner = random.choice([-5, -3, 2, 4, 6])
        left = Linear(factor, factor * inner)
        right = Linear(0, factor * (solution + inner))
        display = f"{factor}(x {'+' if inner >= 0 else '−'} {abs(inner)}) = {num(right.c)}"
        simplify = True
    else:
        a, extra = random.choice([(2, 3), (3, 2), (4, 2)])
        b = random.choice([-5, -2, 3, 6])
        left = Linear(a + extra, b)
        right = Linear(0, (a + extra) * solution + b)
        sign = "+" if b >= 0 else "−"
        display = f"{a}x + {extra}x {sign} {abs(b)} = {num(right.c)}"
        simplify = True
    return {"left": left, "right": right, "display": display, "solution": solution, "simplify": simplify}


def fresh(level, mode, position=1):
    p = make_problem(level)
    st.session_state.problem = p
    st.session_state.current_left = p["left"]
    st.session_state.current_right = p["right"]
    st.session_state.original_line = p["display"] or equation(p["left"], p["right"])
    st.session_state.lines = [("Original equation", st.session_state.original_line)]
    st.session_state.phase = "simplify" if p["simplify"] else "choose"
    st.session_state.pending = None
    st.session_state.feedback = ("info", "Choose a useful inverse operation." if not p["simplify"] else "Distribute or combine like terms first.")
    st.session_state.problem_number = position
    st.session_state.step_count = 0
    st.session_state.last_move = None
    st.session_state.mastery_clean = True
    st.session_state.hints_used = 0
    st.session_state.mastery_clean = True
    for key in ("amount_input", "new_left", "new_right", "simplify_left", "simplify_right", "verify_input"):
        st.session_state.pop(key, None)


def isolated(left, right):
    return left.close(Linear(1, 0)) and abs(right.x) < 1e-7


def feedback(kind, message):
    st.session_state.feedback = (kind, message)


def operation(left, right, symbol, number, target):
    if symbol in ("+", "−"):
        amount = number if symbol == "+" else -number
        shift = Linear(amount if target == "x" else 0, amount if target == "number" else 0)
        return left + shift, right + shift
    factor = number if symbol == "×" else 1 / number
    return left.times(factor), right.times(factor)


def scale_svg(left_text, right_text):
    left_text = html.escape(left_text)
    right_text = html.escape(right_text)
    return f"""
    <svg viewBox="0 0 520 205" style="width:100%;max-height:220px" role="img" aria-label="Balanced scale with left and right sides of the equation">
      <path d="M260 77V176" stroke="#92a7b8" stroke-width="13" stroke-linecap="round"/>
      <path d="M218 182H302" stroke="#92a7b8" stroke-width="12" stroke-linecap="round"/>
      <path d="M74 78H446" stroke="#7896ae" stroke-width="9" stroke-linecap="round"/>
      <circle cx="260" cy="78" r="12" fill="#2563eb"/>
      <path d="M74 78L34 143M74 78L114 143M446 78L406 143M446 78L486 143"
            stroke="#97a7b8" stroke-width="3" fill="none"/>
      <path d="M8 143Q74 186 140 143Z" fill="#bfdbfe" stroke="#729ac5" stroke-width="3"/>
      <path d="M380 143Q446 186 512 143Z" fill="#bfdbfe" stroke="#729ac5" stroke-width="3"/>
      <rect x="9" y="108" width="130" height="35" rx="8" fill="#dbeafe" stroke="#93c5fd"/>
      <rect x="381" y="108" width="130" height="35" rx="8" fill="#dbeafe" stroke="#93c5fd"/>
      <text x="74" y="130" font-family="Arial,sans-serif" font-size="15" font-weight="bold" text-anchor="middle" fill="#1e40af" textLength="{min(112, max(36, len(left_text) * 9))}" lengthAdjust="spacingAndGlyphs">{left_text}</text>
      <text x="446" y="130" font-family="Arial,sans-serif" font-size="15" font-weight="bold" text-anchor="middle" fill="#1e40af" textLength="{min(112, max(36, len(right_text) * 9))}" lengthAdjust="spacingAndGlyphs">{right_text}</text>
      <text x="260" y="28" font-family="Arial,sans-serif" text-anchor="middle" font-size="14" fill="#64748b">Same operation · Both sides</text>
    </svg>"""



st.markdown("""
<style>
html,body,[data-testid="stApp"],button,input,select {font-family:Inter,Arial,sans-serif!important}
.block-container {max-width:1020px;padding-top:1.4rem}
h1,h2,h3 {font-family:Inter,Arial,sans-serif!important}
.eyebrow {font-size:12px;text-transform:uppercase;letter-spacing:1.2px;font-weight:800;color:#64748b}
.eq-current {font-size:clamp(24px,4vw,36px);font-weight:800;text-align:center;color:#1d4ed8;padding:10px 0}
.balance-guide {text-align:center;font-size:13px;color:#64748b;margin-bottom:3px}
.equation-action {display:grid;grid-template-columns:minmax(0,1fr) 32px minmax(0,1fr);align-items:center;gap:4px;
max-width:650px;margin:10px auto;padding:12px;border:1px solid #cbd5e1;border-radius:12px;background:#f8fbff}
.equation-action .side {text-align:center;min-width:0}
.equation-action .term {font-size:clamp(19px,3vw,27px);font-weight:750;color:#172554;overflow-wrap:anywhere}
.equation-action .action {display:inline-block;margin-top:8px;padding:5px 17px;border-radius:8px;background:#dbeafe;color:#1d4ed8;
font-weight:800;font-size:20px;border-bottom:2px solid #2563eb}
.equation-action .equals {font-size:25px;text-align:center;font-weight:800;color:#334155}
.work-line {border-bottom:1px solid #cbd5e1;padding:11px 7px}
.work-line .note {font-size:12px;color:#64748b}
.work-line .math {font-size:21px;font-weight:700;color:inherit;margin-top:3px;overflow-wrap:anywhere}
.check-math {font-size:clamp(20px,3vw,28px);font-weight:750;text-align:center;padding:8px 4px;margin:3px 0 14px;color:#1d4ed8;overflow-wrap:anywhere}
.routine {background:#f1f5f9;border-radius:10px;padding:12px;font-size:14px;color:#334155;line-height:1.9}
@media(max-width:640px){.equation-action{padding:8px}.equation-action .action{font-size:16px;padding:4px 8px}}
</style>
""", unsafe_allow_html=True)

st.title("⚖️ Equation Balance Lab")
st.caption("The goal isn't just to find x. It's to show how each move keeps the equation balanced.")

if "student" not in st.session_state:
    st.session_state.student = ""
if "level" not in st.session_state:
    st.session_state.level = 1
if "mode" not in st.session_state:
    st.session_state.mode = "Practice"
if "results" not in st.session_state:
    st.session_state.results = {1: [], 2: [], 3: []}
if "mastery_correct" not in st.session_state:
    st.session_state.mastery_correct = 0
if "mastery_finished" not in st.session_state:
    st.session_state.mastery_finished = False
if "practice_solved" not in st.session_state:
    st.session_state.practice_solved = {1: 0, 2: 0, 3: 0}

if not st.session_state.student:
    st.subheader("Welcome!")
    st.write("Enter your first and last name to begin.")
    with st.form("student_name"):
        first = st.text_input("First name")
        last = st.text_input("Last name")
        go = st.form_submit_button("Start learning", type="primary")
    if go:
        if first.strip() and last.strip():
            st.session_state.student = f"{first.strip()} {last.strip()}"
            st.rerun()
        else:
            st.warning("Enter both your first and last name.")
    st.caption("Progress in this prototype lasts only for your current browser session.")
    st.stop()

top1, top2 = st.columns([4, 1])
with top1:
    st.caption(f"Student: {st.session_state.student}")
with top2:
    if st.button("Change student"):
        for k in ("student", "loaded_for", "problem", "results", "mastery_correct",
                  "mastery_finished", "practice_solved"):
            st.session_state.pop(k, None)
        st.rerun()

level_names = {1: "One-Step", 2: "Two-Step", 3: "Multi-Step"}
level = st.segmented_control(
    "Choose your level", [1, 2, 3],
    format_func=lambda value: f"Level {value} · {level_names[value]}",
    key="level"
)
if level is None:
    level = 1
mode = st.radio("Choose an activity", ["Practice", "Mastery Check"], horizontal=True, key="mode")

if st.session_state.get("loaded_for") != (level, mode):
    st.session_state.loaded_for = (level, mode)
    st.session_state.mastery_correct = 0
    st.session_state.mastery_finished = False
    fresh(level, mode)

if mode == "Mastery Check":
    st.info("Mastery Check · 5 problems · 4 correct on the first try to pass · no hints.")
    st.progress((st.session_state.problem_number - 1) / 5,
                text=f"Problem {st.session_state.problem_number} of 5 · {st.session_state.mastery_correct} correct")
else:
    st.caption(f"Practice problems completed: {st.session_state.practice_solved[level]}")

if st.session_state.mastery_finished:
    score = st.session_state.mastery_correct
    if score >= 4:
        st.success(f"Level {level} mastered! You solved {score} out of 5 correctly on the first try.")
    else:
        st.warning(f"You solved {score} out of 5 correctly on the first try. Keep practicing and try again.")
    if st.button("Try a fresh mastery check", type="primary"):
        st.session_state.mastery_correct = 0
        st.session_state.mastery_finished = False
        fresh(level, mode, 1)
        st.rerun()
    st.stop()

p = st.session_state.problem
l = st.session_state.current_left
r = st.session_state.current_right
phase = st.session_state.phase

main, work = st.columns([1.25, 0.75], gap="large")
with main:
    st.markdown(f'<div class="eyebrow">Level {level} · {level_names[level]} · '
                + ("Problem " + str(st.session_state.problem_number))
                + '</div>', unsafe_allow_html=True)
    current_text = p["display"] if phase == "simplify" and p["display"] else equation(l, r)
    st.markdown(f'<div class="eq-current">{html.escape(current_text)}</div>', unsafe_allow_html=True)

    # The scale is the physical picture. The action grid below it is the symbolic picture.
    scale_left = p["display"].split("=")[0].strip() if phase == "simplify" and p["display"] else expression(l)
    scale_right = p["display"].split("=")[1].strip() if phase == "simplify" and p["display"] else expression(r)
    st.markdown('<div class="balance-guide">The two pans represent equal quantities.</div>', unsafe_allow_html=True)
    st.markdown(scale_svg(scale_left, scale_right), unsafe_allow_html=True)

    if phase == "simplify":
        st.markdown("### 1 · Simplify first")
        st.write("Before using inverse operations, distribute or combine like terms.")
        with st.form("simplify"):
            c1, mid, c2 = st.columns([5, 1, 5])
            with c1:
                a = st.text_input("New LEFT expression", key="simplify_left", placeholder="e.g. 3x + 6")
            with mid:
                st.markdown("### =")
            with c2:
                b = st.text_input("New RIGHT expression", key="simplify_right", placeholder="e.g. 18")
            confirmed = st.form_submit_button("Check my simplified equation", type="primary")
        if confirmed:
            try:
                a_val, b_val = parse_linear(a), parse_linear(b)
                if "(" in a + b or ")" in a + b:
                    feedback("error", "Finish distributing before continuing. Remove the parentheses.")
                    st.session_state.mastery_clean = False
                elif a_val.close(l) and b_val.close(r):
                    st.session_state.lines.append(("Simplified both expressions", equation(l, r)))
                    st.session_state.phase = "choose"
                    feedback("success", "Equivalent equation! Now decide which operation to undo.")
                    st.rerun()
                else:
                    st.session_state.mastery_clean = False
                    feedback("error", "Not equivalent yet. Check distribution and like terms.")
            except (SyntaxError, ValueError, TypeError, ZeroDivisionError):
                st.session_state.mastery_clean = False
                feedback("error", "Enter expressions such as 3x + 6 and 18.")

    elif phase == "choose":
        current_step = st.session_state.step_count + 1
        st.markdown(f"### Step {current_step} · Choose your move")
        if current_step > 1:
            st.info("This is your NEW starting equation. Look at it and choose the next inverse operation.")
        else:
            st.write("What do you want to **undo** to get x alone?")
        if mode == "Practice" and current_step > 1:
            if abs(r.x) > 1e-8:
                st.caption("Look for x terms on both sides. How could you put the x terms together?")
            elif abs(l.c) > 1e-8:
                st.caption("There is still a number added to or subtracted from the x term. What would undo it?")
            elif abs(l.x - 1) > 1e-8:
                st.caption("The x term still has a coefficient. What would make that coefficient 1?")
        with st.form("choose_operation"):
            oc1, oc2 = st.columns([1.1, 1])
            with oc1:
                symbol = st.radio("Operation", ["−", "+", "÷", "×"],
                                  horizontal=True)
            with oc2:
                amount = st.number_input("By how much?", value=1.0, step=1.0)
            target = "number"
            if level == 3:
                target = st.radio("What are you moving?", ["number", "x terms"], horizontal=True)
            clicked = st.form_submit_button("Show this move on BOTH sides →", type="primary")
        if clicked:
            if abs(amount) < 1e-10:
                feedback("error", "Choose a nonzero number.")
            elif target == "x terms" and symbol in ("÷", "×"):
                feedback("error", "Use addition or subtraction to move x terms.")
            else:
                new_l, new_r = operation(l, r, symbol, amount, "x" if target == "x terms" else "number")
                if new_l.close(l) and new_r.close(r):
                    feedback("error", "That move changes nothing. Try a useful operation.")
                else:
                    st.session_state.pending = (symbol, amount, target, new_l, new_r)
                    st.session_state.phase = "write"
                    feedback("info", "Look at the matching blue operations. Now calculate each side yourself.")
                    st.rerun()

    elif phase == "write":
        symbol, amount, target, expected_l, expected_r = st.session_state.pending
        operation_label = f"{symbol} {num(amount)}{'x' if target == 'x terms' else ''}"
        st.markdown("### 2 · Apply the same move to EACH side")
        st.write("The blue labels show your chosen operation. The two sides must get exactly the same treatment.")
        action = html.escape(operation_label)
        st.markdown(
            '<div class="equation-action">'
            f'<div class="side"><div class="term">{html.escape(expression(l))}</div><div class="action">{action}</div></div>'
            '<div class="equals">=</div>'
            f'<div class="side"><div class="term">{html.escape(expression(r))}</div><div class="action">{action}</div></div>'
            '</div>', unsafe_allow_html=True)
        st.markdown("### 3 · Write the resulting equation")
        st.write("Work out each side. Write what is left after the operation.")
        with st.form("write_new_line"):
            lc, equal, rc = st.columns([5, 1, 5])
            with lc:
                entered_left = st.text_input("New LEFT side", key="new_left",
                                             placeholder="e.g. 3x")
            with equal:
                st.markdown("### =")
            with rc:
                entered_right = st.text_input("New RIGHT side", key="new_right",
                                              placeholder="e.g. 15")
            checked = st.form_submit_button("Check my new equation →", type="primary")
        if checked:
            try:
                a = parse_linear(entered_left)
                b = parse_linear(entered_right)
                if a.close(expected_l) and b.close(expected_r):
                    st.session_state.current_left = expected_l
                    st.session_state.current_right = expected_r
                    st.session_state.lines.append((f"{operation_label} on both sides",
                                                   equation(expected_l, expected_r)))
                    st.session_state.step_count += 1
                    st.session_state.pending = None
                    st.session_state.last_move = {
                        "before": equation(l, r),
                        "operation": operation_label,
                        "after": equation(expected_l, expected_r)
                    }
                    if isolated(expected_l, expected_r):
                        # The student has already written x = value. Don't ask for it twice.
                        value = expected_r.c
                        left_check = p["left"].x * value + p["left"].c
                        right_check = p["right"].x * value + p["right"].c
                        st.session_state.lines.append((
                            "Verified in the original equation",
                            f"{num(left_check)} = {num(right_check)}"
                        ))
                        st.session_state.phase = "complete"
                        if mode == "Mastery Check" and st.session_state.mastery_clean:
                            st.session_state.mastery_correct += 1
                        elif mode == "Practice":
                            st.session_state.practice_solved[level] += 1
                        feedback("success", "You isolated x and the original equation balances.")
                    else:
                        st.session_state.phase = "transition"
                        feedback("success", "Correct. You have written a new equivalent equation.")
                    st.rerun()
                st.session_state.mastery_clean = False
                if mode == "Practice" and a.close(expected_l):
                    feedback("error", "The LEFT side is correct. Recalculate the RIGHT side.")
                elif mode == "Practice" and b.close(expected_r):
                    feedback("error", "The RIGHT side is correct. Recalculate the LEFT side.")
                else:
                    feedback("error", "That line doesn't match the blue operation on both sides. Try again.")
            except (SyntaxError, ValueError, TypeError, ZeroDivisionError):
                st.session_state.mastery_clean = False
                feedback("error", "Type expressions like 3x, x, 15, or 2x − 4.")

    elif phase == "transition":
        last = st.session_state.last_move
        next_step = st.session_state.step_count + 1
        st.success("✓ Step complete! You kept the equation balanced.")
        with st.container(border=True):
            st.caption("YOUR PREVIOUS EQUATION")
            st.markdown(f"#### {last['before']}")
            st.caption(f"YOU APPLIED {last['operation']} TO BOTH SIDES")
            st.markdown("↓")
            st.caption("YOUR NEW EQUATION — THIS IS WHERE YOU START NEXT")
            st.markdown(f"### :blue[{last['after']}]")
        st.write("You are **not finished yet**. Look at the new equation and decide what to undo next.")
        if st.button(f"Continue to Step {next_step} →", type="primary", use_container_width=True):
            st.session_state.phase = "choose"
            feedback("info", f"Step {next_step}: choose the next inverse operation for {last['after']}.")
            st.rerun()

    elif phase == "complete":
        solved_value = st.session_state.current_right.c
        st.success(f"Equation solved: x = {num(solved_value)}")
        show_solution_check(p, st.session_state.original_line, solved_value)
        if mode == "Mastery Check" and not st.session_state.mastery_clean:
            st.warning("You completed the equation with a correction, so this problem does not earn a mastery point.")
        label = "Next practice equation →" if mode == "Practice" else "Next mastery equation →"
        if st.button(label, type="primary"):
            if mode == "Mastery Check" and st.session_state.problem_number >= 5:
                st.session_state.mastery_finished = True
                st.session_state.results[level].append({
                    "student": st.session_state.student,
                    "correct": st.session_state.mastery_correct,
                    "total": 5,
                    "passed": st.session_state.mastery_correct >= 4
                })
            else:
                fresh(level, mode, st.session_state.problem_number + 1)
            st.rerun()

    kind, message = st.session_state.feedback
    if kind == "success":
        st.success(message)
    elif kind == "error":
        st.error(message)
    else:
        st.info(message)

    if mode == "Practice" and phase in ("simplify", "choose", "write"):
        if st.button("Need a hint?"):
            if phase == "simplify":
                st.info("Distribute to every term in the parentheses, then combine the x terms.")
            elif phase == "write":
                st.info("Start with the left expression, apply the blue operation, simplify. Repeat separately on the right.")
            elif abs(r.x) > 1e-8:
                st.info("Try removing the x term from the right by subtracting the same x term on both sides.")
            elif abs(l.c) > 1e-8:
                st.info(f"The left expression has {'+' if l.c > 0 else '−'} {num(abs(l.c))}. Undo that first.")
            else:
                st.info("What would make the coefficient in front of x equal to 1?")

    if mode == "Practice" and phase == "write":
        if st.button("↶ Change my operation"):
            st.session_state.pending = None
            st.session_state.phase = "choose"
            feedback("info", "Choose a different operation to apply to both sides.")
            st.rerun()

with work:
    st.markdown("### My algebra steps")
    st.caption("One line for each move. Every line should be equal to the one before it.")
    with st.container(border=True):
        for i, (note, line) in enumerate(st.session_state.lines):
            st.markdown(
                f'<div class="work-line"><div class="note">{"START" if i == 0 else "STEP " + str(i)} · {html.escape(note)}</div>'
                f'<div class="math">{html.escape(line)}</div></div>',
                unsafe_allow_html=True)
        if phase == "write":
            st.caption("↓ Your next equation goes here.")
        elif phase == "transition":
            st.caption("✓ New equation recorded. Use Continue to start the next step.")
    st.markdown(
        '<div class="routine"><b>Our routine</b><br>'
        '① Choose an inverse operation<br>'
        '② Do it to <b>BOTH</b> sides<br>'
        '③ Write the resulting equation<br>'
        '④ Click <b>Continue to next step</b><br>'
        '⑤ Repeat until x is alone; the app checks your answer</div>',
        unsafe_allow_html=True)

st.divider()
st.caption("Prototype: names are not authenticated, and progress lasts only for this browser session. A database and teacher dashboard will be needed before using mastery results as official student records.")
