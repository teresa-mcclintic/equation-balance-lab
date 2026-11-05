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
    st.session_state.mastery_clean = True
    st.session_state.hints_used = 0
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
html,body,[class*="css"],[data-testid="stApp"] {font-family: Inter, Arial, sans-serif;}
.block-container {max-width:1050px;padding-top:2rem}
h1,h2,h3,p,label,button,input {font-family:Inter,Arial,sans-serif!important}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:14px}
.eqbig {font-size:clamp(23px,3.3vw,36px);font-weight:800;text-align:center;padding:12px 4px;color:#1d4ed8}
.step-line {padding:9px 14px;border-bottom:1px solid #cbd5e1;font-size:20px;font-weight:650}
.step-note {font-size:12px;color:#64748b;font-weight:500}
</style>
""", unsafe_allow_html=True)
st.title("⚖️ Equation Balance Lab")
st.caption("Choose an inverse operation → apply it to BOTH sides → write the new equation → check.")

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
if "mastery_awarded" not in st.session_state:
    st.session_state.mastery_awarded = False
if "practice_solved" not in st.session_state:
    st.session_state.practice_solved = {1: 0, 2: 0, 3: 0}

if not st.session_state.student:
    st.subheader("Student sign-in")
    st.write("Enter your first and last name to begin. No password or school email is needed.")
    with st.form("student_name"):
        first = st.text_input("First name")
        last = st.text_input("Last name")
        entered = st.form_submit_button("Start learning", type="primary")
    if entered:
        if first.strip() and last.strip():
            st.session_state.student = f"{first.strip()} {last.strip()}"
            st.rerun()
        else:
            st.warning("Please enter both your first and last name.")
    st.info("Prototype note: progress is saved only during this browser session. A permanent database and teacher dashboard are planned for a later release.")
    st.stop()

top1, top2 = st.columns([3, 1])
with top1:
    st.write(f"**Student:** {st.session_state.student}")
with top2:
    if st.button("Change student"):
        for k in ("student", "problem", "results", "mastery_correct", "mastery_finished", "mastery_awarded", "practice_solved"):
            st.session_state.pop(k, None)
        st.rerun()

level_labels = ["One-Step", "Two-Step", "Multi-Step"]
level = st.segmented_control("Choose a level", options=[1, 2, 3], format_func=lambda x: f"Level {x}: {level_labels[x-1]}", key="level")
if level is None:
    level = 1
mode = st.radio("Activity", ["Practice", "Mastery Check"], horizontal=True, key="mode")
identifier = (level, mode)
if st.session_state.get("loaded_for") != identifier:
    st.session_state.loaded_for = identifier
    st.session_state.mastery_correct = 0
    st.session_state.mastery_finished = False
    st.session_state.mastery_awarded = False
    fresh(level, mode)

if mode == "Mastery Check":
    st.info("Mastery: 5 equations, 4 correct on the first attempt to pass. No hints. Every equation must be solved by writing algebraic steps.")
    count = st.session_state.problem_number
    st.progress(min((count - 1) / 5, 1.0), text=f"Question {count} of 5 · {st.session_state.mastery_correct} correct so far")
else:
    st.caption(f"Practice problems solved this session: {st.session_state.practice_solved[level]}")

if st.session_state.mastery_finished:
    correct = st.session_state.mastery_correct
    passed = correct >= 4
    st.success(f"Mastery {'achieved' if passed else 'not yet achieved'}: {correct}/5 correct ({correct * 20}%).") if passed else st.warning(f"Mastery not yet achieved: {correct}/5 correct ({correct * 20}%).")
    st.write("You can retry with a new set of questions.")
    if st.button("Start another mastery check", type="primary"):
        st.session_state.mastery_correct = 0
        st.session_state.mastery_finished = False
        st.session_state.mastery_awarded = False
        fresh(level, mode)
        st.rerun()
    st.stop()

left, right = st.columns([1.2, 0.8], gap="large")
p = st.session_state.problem
l = st.session_state.current_left
r = st.session_state.current_right
phase = st.session_state.phase
with left:
    st.subheader(f"Level {level} · {level_labels[level-1]}")
    shown_l = p["display"].split("=")[0].strip() if phase == "simplify" and p["display"] else expression(l)
    shown_r = p["display"].split("=")[1].strip() if phase == "simplify" and p["display"] else expression(r)
    st.markdown(f'<div class="eqbig">{html.escape(shown_l)} = {html.escape(shown_r)}</div>', unsafe_allow_html=True)
    st.markdown(scale_svg(shown_l, shown_r), unsafe_allow_html=True)

    if phase == "simplify":
        st.markdown("#### Step 1 · Simplify")
        st.write("Distribute and/or combine like terms. Write the simplified equation.")
        with st.form("simplify_form"):
            a, center, b = st.columns([5, 1, 5])
            with a:
                new_l = st.text_input("Left side", key="simplify_left", placeholder="e.g. 3x + 6")
            with center:
                st.markdown("### =")
            with b:
                new_r = st.text_input("Right side", key="simplify_right", placeholder="e.g. 18")
            submit = st.form_submit_button("Check simplification", type="primary")
        if submit:
            try:
                left_t, right_t = parse_linear(new_l), parse_linear(new_r)
                if "(" in new_l + new_r or ")" in new_l + new_r:
                    feedback("error", "Finish distributing; the simplified equation shouldn't contain parentheses.")
                elif left_t.close(l) and right_t.close(r):
                    st.session_state.lines.append(("Distribute / combine like terms", equation(l, r)))
                    st.session_state.phase = "choose"
                    feedback("success", "Yes. Your simplified equation is equivalent to the original.")
                    st.rerun()
                else:
                    st.session_state.mastery_clean = False
                    feedback("error", "Not equivalent yet. Check the distribution and like terms.")
            except (SyntaxError, ValueError, ZeroDivisionError, TypeError):
                st.session_state.mastery_clean = False
                feedback("error", "Use a linear expression such as 3x + 6 on each side.")

    elif phase == "choose":
        if isolated(l, r):
            st.session_state.phase = "verify"
            st.rerun()
        st.markdown("#### Step 1 · Choose an inverse operation")
        st.write("What should you do to **both** sides?")
        with st.form("operation_form"):
            c1, c2, c3 = st.columns([2, 2, 2])
            with c1:
                symbol = st.selectbox("Operation", ["−", "+", "÷", "×"])
            with c2:
                amount = st.number_input("Number", value=1.0, step=1.0)
            with c3:
                target = st.selectbox("Apply to", ["number", "x terms"] if level == 3 else ["number"])
            apply_clicked = st.form_submit_button("Apply to BOTH sides", type="primary")
        if apply_clicked:
            if abs(amount) < 1e-10:
                feedback("error", "Use a nonzero value. Division by zero is never allowed.")
            elif target == "x terms" and symbol in ("×", "÷"):
                feedback("error", "To move x terms, use addition or subtraction.")
            else:
                next_l, next_r = operation(l, r, symbol, amount, "x" if target == "x terms" else "number")
                if next_l.close(l) and next_r.close(r):
                    feedback("error", "That operation does not change the equation. Try a useful move.")
                else:
                    st.session_state.pending = (symbol, amount, target, next_l, next_r)
                    st.session_state.phase = "write"
                    feedback("info", "Now calculate the results and write the new equation yourself.")
                    st.rerun()

    elif phase == "write":
        symbol, amount, target, expected_l, expected_r = st.session_state.pending
        st.markdown("#### Step 2 · Write the new equation")
        st.markdown(f"**Your move:** {symbol} {num(amount)}{'x' if target == 'x terms' else ''} on **each side**.")
        st.write("Enter the result on the left and the result on the right.")
        with st.form("write_form"):
            a, center, b = st.columns([5, 1, 5])
            with a:
                new_l = st.text_input("New left side", key="new_left", placeholder="e.g. 3x")
            with center:
                st.markdown("### =")
            with b:
                new_r = st.text_input("New right side", key="new_right", placeholder="e.g. 15")
            checked = st.form_submit_button("Check my new equation", type="primary")
        if checked:
            try:
                entered_l, entered_r = parse_linear(new_l), parse_linear(new_r)
                left_ok, right_ok = entered_l.close(expected_l), entered_r.close(expected_r)
                if left_ok and right_ok:
                    st.session_state.current_left = expected_l
                    st.session_state.current_right = expected_r
                    note = f"{symbol} {num(amount)}{'x' if target == 'x terms' else ''} on both sides"
                    st.session_state.lines.append((note, equation(expected_l, expected_r)))
                    st.session_state.step_count += 1
                    st.session_state.pending = None
                    st.session_state.phase = "verify" if isolated(expected_l, expected_r) else "choose"
                    feedback("success", "Both sides are correct. You kept the equation balanced.")
                    st.rerun()
                elif mode == "Mastery Check":
                    st.session_state.mastery_clean = False
                    feedback("error", "That line isn't correct yet. Recalculate both sides.")
                elif left_ok:
                    feedback("error", "Your left side is correct. Recheck the right side.")
                elif right_ok:
                    feedback("error", "Your right side is correct. Recheck the left side.")
                else:
                    feedback("error", "Recalculate both sides using your selected operation.")
            except (SyntaxError, ValueError, ZeroDivisionError, TypeError):
                st.session_state.mastery_clean = False
                feedback("error", "Enter expressions such as x, 3x, 3x − 5, or 12.")

    elif phase == "verify":
        st.markdown("#### Final step · Verify")
        st.write("Enter the value of x, then check it against the **original equation**.")
        with st.form("verify_form"):
            solution_input = st.number_input("x =", value=0.0, step=1.0, key="verify_input")
            verify_clicked = st.form_submit_button("Check my solution", type="primary")
        if verify_clicked:
            original_l = p["left"].x * solution_input + p["left"].c
            original_r = p["right"].x * solution_input + p["right"].c
            if abs(original_l - original_r) < 1e-7 and abs(solution_input - p["solution"]) < 1e-7 and st.session_state.step_count > 0:
                st.session_state.lines.append(("Verified by substitution", f"{num(original_l)} = {num(original_r)}"))
                st.session_state.phase = "complete"
                if mode == "Mastery Check" and st.session_state.mastery_clean:
                    st.session_state.mastery_correct += 1
                else:
                    st.session_state.practice_solved[level] += 1
                feedback("success", "Correct! Your solution makes both sides equal.")
                st.rerun()
            else:
                st.session_state.mastery_clean = False
                feedback("error", "That value does not make the original equation balanced. Try again.")

    elif phase == "complete":
        st.success("Equation solved! Your steps are recorded on the right.")
        if mode == "Mastery Check" and not st.session_state.mastery_clean:
            st.warning("This question was completed with corrections and does not earn a mastery point. You can continue to the next question.")
        if mode == "Practice":
            if st.button("Next practice equation →", type="primary"):
                fresh(level, mode, st.session_state.problem_number + 1)
                st.rerun()
        else:
            if st.button("Next mastery equation →", type="primary"):
                if st.session_state.problem_number >= 5:
                    st.session_state.mastery_finished = True
                    st.session_state.results[level].append({
                        "student": st.session_state.student,
                        "correct": st.session_state.mastery_correct,
                        "total": 5,
                        "passed": st.session_state.mastery_correct >= 4,
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

    if mode == "Practice" and phase not in ("complete",):
        if st.button("Show a hint"):
            st.session_state.hints_used += 1
            if phase == "simplify":
                st.info("Multiply the factor outside the parentheses by every term inside, then combine x terms.")
            elif phase == "write":
                st.info("Apply the operation to each side separately. Then simplify the expression on each side.")
            elif phase == "verify":
                st.info("Substitute your proposed x value into the original equation.")
            elif abs(r.x) > 1e-7:
                st.info("There are x terms on both sides. Try subtracting the x term on the right from both sides.")
            elif abs(l.c) > 1e-7:
                st.info(f"Undo the constant on the left. Think about the opposite of {'adding' if l.c > 0 else 'subtracting'} {num(abs(l.c))}.")
            else:
                st.info("Make the coefficient of x equal to 1. What operation undoes multiplication?")

with right:
    st.subheader("My Algebra Steps")
    st.caption("Each line must be an equivalent equation.")
    with st.container(border=True):
        for note, line in st.session_state.lines:
            st.markdown(f'<div class="step-line"><span class="step-note">{html.escape(note)}</span><br>{html.escape(line)}</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("**Our solving routine**")
        st.write("1. Choose an inverse operation.")
        st.write("2. Apply it to both sides.")
        st.write("3. Write the new equation.")
        st.write("4. Repeat, then verify.")

st.divider()
st.caption("Teacher note: This first release saves progress only in the active Streamlit session. Names are not authenticated, and results are not yet a durable student record. Do not treat the mastery scores as secure until persistent storage and teacher access controls are added.")
