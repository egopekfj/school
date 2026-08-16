import copy
import json
import os
import random
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ============================================================
# Файл статистики
# ============================================================
STATS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "test_statistics.json"
)

# ============================================================
# Режимы проверки письменных ответов
# ============================================================
CHECK_MODE_DISPLAY = {
    "exact": "Точное совпадение",
    "contains": "Содержит правильный ответ",
    "letter": "Только пропущенная буква",
    "dash": "Пропуск / Дефис (-)",
}

CHECK_MODE_INTERNAL = {v: k for k, v in CHECK_MODE_DISPLAY.items()}


# ============================================================
# Вспомогательные функции и буфер обмена
# ============================================================
def add_context_menu(widget):
  """Добавляет контекстное меню (ПКМ) и горячие клавиши Ctrl+C/V/X/A с поддержкой раскладок."""

  def copy_text(e=None):
    try:
      widget.event_generate("<<Copy>>")
    except Exception:
      pass
    return "break"

  def paste_text(e=None):
    try:
      widget.event_generate("<<Paste>>")
    except Exception:
      pass
    return "break"

  def cut_text(e=None):
    try:
      widget.event_generate("<<Cut>>")
    except Exception:
      pass
    return "break"

  def select_all(e=None):
    try:
      if isinstance(widget, tk.Text):
        widget.tag_add("sel", "1.0", "end")
      elif isinstance(widget, tk.Entry):
        widget.select_range(0, tk.END)
    except Exception:
      pass
    return "break"

  menu = tk.Menu(widget, tearoff=0)
  menu.add_command(label="Вырезать", command=cut_text)
  menu.add_command(label="Копировать", command=copy_text)
  menu.add_command(label="Вставить", command=paste_text)
  menu.add_separator()
  menu.add_command(label="Выделить всё", command=select_all)

  def show_menu(event):
    menu.post(event.x_root, event.y_root)

  widget.bind("<Button-3>", show_menu)

  # Поддержка русской и английской раскладок
  for keysym in ["c", "C", "Cyrillic_es", "Cyrillic_ES"]:
    widget.bind(f"<Control-{keysym}>", copy_text)
  for keysym in ["v", "V", "Cyrillic_m", "Cyrillic_M"]:
    widget.bind(f"<Control-{keysym}>", paste_text)
  for keysym in ["x", "X", "Cyrillic_ch", "Cyrillic_CH"]:
    widget.bind(f"<Control-{keysym}>", cut_text)
  for keysym in ["a", "A", "Cyrillic_f", "Cyrillic_F"]:
    widget.bind(f"<Control-{keysym}>", select_all)


def setup_fullscreen(window):
  """Настройка полноэкранного режима по F11 и кнопки."""
  window.attributes("-fullscreen", False)

  def toggle_fullscreen(event=None):
    state = not window.attributes("-fullscreen")
    window.attributes("-fullscreen", state)
    return "break"

  def end_fullscreen(event=None):
    window.attributes("-fullscreen", False)
    return "break"

  window.bind("<F11>", toggle_fullscreen)
  window.bind("<Escape>", end_fullscreen)
  return toggle_fullscreen


def safe_float(value, default=0.0):
  if value is None:
    return default
  try:
    if isinstance(value, str):
      value = value.replace(",", ".")
    return float(value)
  except Exception:
    return default


def format_number(value):
  if value is None:
    return ""
  try:
    x = float(value)
  except Exception:
    return str(value)
  if x.is_integer():
    return str(int(x))
  return f"{x:.2f}".rstrip("0").rstrip(".")


def load_statistics():
  if not os.path.exists(STATS_FILE):
    return []
  try:
    with open(STATS_FILE, "r", encoding="utf-8") as f:
      data = json.load(f)
      return data if isinstance(data, list) else []
  except Exception:
    return []


def save_statistics(stats):
  with open(STATS_FILE, "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)


def append_statistics(record):
  stats = load_statistics()
  stats.append(record)
  save_statistics(stats)


def normalize_answer(text):
  if not isinstance(text, str):
    text = str(text)
  text = text.strip().lower().replace("ё", "е")
  for ch in ".,!?;:()[]{}\"'«»":
    text = text.replace(ch, "")
  return " ".join(text.split())


def get_answers_list(q):
  answers = q.get("answers", [])
  if isinstance(answers, str):
    answers = [ans.strip() for ans in answers.split(";") if ans.strip()]
  elif isinstance(answers, list):
    answers = [str(ans).strip() for ans in answers if str(ans).strip()]
  else:
    answers = []

  if not answers and q.get("correct_text"):
    raw = str(q.get("correct_text"))
    answers = [ans.strip() for ans in raw.split(";") if ans.strip()]
  return answers


def contains_correct_answer(user_answer, accepted_answers):
  user_norm = normalize_answer(user_answer)
  if not user_norm:
    return False
  user_tokens = set(user_norm.split())

  for accepted in accepted_answers:
    acc_norm = normalize_answer(accepted)
    if not acc_norm:
      continue
    if " " in acc_norm:
      if acc_norm in user_norm:
        return True
    else:
      if acc_norm in user_tokens:
        return True
  return False


def contains_any_correct_word(user_answer, accepted_answers):
  user_norm = normalize_answer(user_answer)
  user_tokens = set(user_norm.split())
  if not user_tokens:
    return False

  for accepted in accepted_answers:
    acc_norm = normalize_answer(accepted)
    if not acc_norm:
      continue
    for token in acc_norm.split():
      if token and token in user_tokens:
        return True
  return False


def extract_letters(text, allow_dash=False):
  norm = normalize_answer(text)
  if allow_dash:
    return [ch for ch in norm if ch.isalpha() or ch == "-"]
  return [ch for ch in norm if ch.isalpha()]


def letter_answer_is_correct(user_answer, accepted_answers, allow_dash=False):
  user_letters = extract_letters(user_answer, allow_dash=allow_dash)
  if len(user_letters) != 1:
    return False
  user_letter = user_letters[0]

  for accepted in accepted_answers:
    acc_letters = extract_letters(accepted, allow_dash=allow_dash)
    if not acc_letters:
      continue
    if user_letter == acc_letters[0]:
      return True
  return False


def exact_answer_is_correct(user_answer, accepted_answers):
  user_norm = normalize_answer(user_answer)
  if not user_norm:
    return False
  for accepted in accepted_answers:
    if user_norm == normalize_answer(accepted):
      return True
  return False


def get_question_max_points(q):
  if q.get("type") == "text":
    points = safe_float(q.get("full_points", 1.0), 1.0)
    return max(0.0, points)
  return 1.0


def score_text_question(q, user_answer):
  answers = get_answers_list(q)
  full_points = safe_float(q.get("full_points", 1.0), 1.0)
  partial_points = safe_float(q.get("partial_points", 0.0), 0.0)

  if not user_answer or not str(user_answer).strip():
    return 0.0

  mode = q.get("check_mode", "exact")

  if mode == "contains":
    if contains_correct_answer(user_answer, answers):
      return full_points
    if partial_points > 0 and contains_any_correct_word(user_answer, answers):
      return partial_points
    return 0.0

  if mode in ("letter", "dash"):
    allow_dash = mode == "dash"
    if letter_answer_is_correct(
        user_answer, answers, allow_dash=allow_dash
    ) or (allow_dash and user_answer.strip() == "-"):
      return full_points
    return 0.0

  if exact_answer_is_correct(user_answer, answers):
    return full_points
  if partial_points > 0 and contains_any_correct_word(user_answer, answers):
    return partial_points

  return 0.0


# ============================================================
# Главное окно
# ============================================================
class TestApp:

  def __init__(self):
    self.root = tk.Tk()
    self.root.title("📚 Школьный Тест-Приложение")
    self.root.geometry("620x520")
    self.toggle_fs = setup_fullscreen(self.root)
    self.setup_menu()

  def setup_menu(self):
    for w in self.root.winfo_children():
      w.destroy()

    top_bar = tk.Frame(self.root)
    top_bar.pack(fill="x", padx=10, pady=5)
    tk.Button(
        top_bar,
        text="⛶ Полноэкранный режим (F11)",
        command=self.toggle_fs,
        font=("Segoe UI", 9),
    ).pack(side="right")

    tk.Label(
        self.root, text="Выберите режим работы:", font=("Segoe UI", 18, "bold")
    ).pack(pady=(20, 10))

    tk.Button(
        self.root,
        text="👨‍🏫 Конструктор тестов (Учитель)",
        command=self.open_teacher,
        height=2,
        font=("Segoe UI", 13),
        bg="#4361ee",
        fg="white",
        relief="flat",
    ).pack(pady=10, padx=50, fill="x")

    tk.Button(
        self.root,
        text="🎓 Пройти тест (Ученик)",
        command=self.open_student,
        height=2,
        font=("Segoe UI", 13),
        bg="#2a9d8f",
        fg="white",
        relief="flat",
    ).pack(pady=10, padx=50, fill="x")

    tk.Button(
        self.root,
        text="📊 Статистика",
        command=self.open_statistics,
        height=2,
        font=("Segoe UI", 13),
        bg="#f4a261",
        fg="white",
        relief="flat",
    ).pack(pady=10, padx=50, fill="x")

  def open_teacher(self):
    TeacherWindow(self.root)

  def open_student(self):
    StudentWindow(self.root)

  def open_statistics(self):
    StatsWindow(self.root)


# ============================================================
# ИИ Генератор тестов
# ============================================================
class AIGeneratorDialog(tk.Toplevel):

  def __init__(self, parent, callback):
    super().__init__(parent)
    self.title("🤖 ИИ-Помощник создания тестов")
    self.geometry("650x550")
    self.transient(parent)
    self.grab_set()
    self.callback = callback
    setup_fullscreen(self)

    tk.Label(
        self, text="🤖 Генератор вопросов на базе ИИ", font=("Segoe UI", 14, "bold")
    ).pack(pady=10)

    tk.Label(
        self, text="Введите тему теста или вставьте учебный текст:"
    ).pack(anchor="w", padx=15)
    self.txt_prompt = tk.Text(self, height=6, font=("Segoe UI", 10))
    self.txt_prompt.pack(fill="x", padx=15, pady=5)
    add_context_menu(self.txt_prompt)

    opts_frame = tk.Frame(self)
    opts_frame.pack(fill="x", padx=15, pady=5)

    tk.Label(opts_frame, text="Количество вопросов:").pack(side="left")
    self.ent_count = tk.Entry(opts_frame, width=5)
    self.ent_count.pack(side="left", padx=5)
    self.ent_count.insert(0, "3")
    add_context_menu(self.ent_count)

    tk.Button(
        self,
        text="⚡ Сгенерировать вопросы",
        command=self.generate,
        bg="#7209b7",
        fg="white",
        font=("Segoe UI", 11, "bold"),
    ).pack(pady=10)

    tk.Label(
        self, text="Предпросмотр сгенерированных вопросов:"
    ).pack(anchor="w", padx=15)
    self.txt_result = tk.Text(self, height=10, font=("Segoe UI", 10))
    self.txt_result.pack(fill="both", expand=True, padx=15, pady=5)
    add_context_menu(self.txt_result)

    tk.Button(
        self,
        text="➕ Добавить вопросы в тест",
        command=self.add_to_test,
        bg="#2a9d8f",
        fg="white",
        font=("Segoe UI", 11, "bold"),
    ).pack(pady=10)

    self.generated_q = []

  def generate(self):
    prompt = self.txt_prompt.get("1.0", "end").strip()
    if not prompt:
      messagebox.showwarning("Внимание", "Введите тему или текст")
      return

    count = safe_float(self.ent_count.get(), 3)
    count = int(min(max(count, 1), 10))

    self.generated_q = []
    templates = [
        {
            "text": f"Какой основной термин относится к теме '{prompt}'?",
            "type": "choice",
            "options": [
                f"Понятие А ({prompt})",
                "Альтернатива Б",
                "Вариант В",
                "Термин Г",
            ],
            "correct": 0,
            "time": 20,
        },
        {
            "text": f"Вставьте пропущенную букву/знак в слове по теме '{prompt}': пр-вило",
            "type": "text",
            "answers": ["a", "-"],
            "check_mode": "dash",
            "full_points": 1.0,
            "partial_points": 0.0,
            "time": 15,
        },
        {
            "text": (
                f"Напишите ключевое определение или факты по теме '{prompt}'"
            ),
            "type": "text",
            "answers": [prompt],
            "check_mode": "contains",
            "full_points": 2.0,
            "partial_points": 1.0,
            "time": 30,
        },
    ]

    for i in range(count):
      q = copy.deepcopy(templates[i % len(templates)])
      if i >= len(templates):
        q["text"] += f" (Вопрос {i+1})"
      self.generated_q.append(q)

    self.txt_result.delete("1.0", "end")
    for i, q in enumerate(self.generated_q, 1):
      self.txt_result.insert(
          "end", f"{i}. [{q['type']}] {q['text']}\n"
      )

  def add_to_test(self):
    if not self.generated_q:
      messagebox.showwarning("Ошибка", "Сначала сгенерируйте вопросы")
      return
    self.callback(self.generated_q)
    self.destroy()


# ============================================================
# Окно учителя
# ============================================================
class TeacherWindow(tk.Toplevel):

  def __init__(self, parent):
    super().__init__(parent)
    self.title("🛠 Конструктор тестов")
    self.geometry("920x900")
    self.transient(parent)
    self.grab_set()
    self.toggle_fs = setup_fullscreen(self)

    self.test_data = {
        "title": "Новый тест",
        "take_questions": 5,
        "grading": {"5": 18, "4": 14, "3": 9, "2": 0},
        "questions": [],
    }

    self.selected_idx = None
    self.editing_idx = None
    self.setup_ui()

  def setup_ui(self):
    main = tk.Frame(self, padx=15, pady=10)
    main.pack(fill=tk.BOTH, expand=True)

    top_bar = tk.Frame(main)
    top_bar.pack(fill="x", pady=(0, 5))

    tk.Button(
        top_bar,
        text="🤖 ИИ-Помощник",
        command=self.open_ai,
        bg="#7209b7",
        fg="white",
        font=("Segoe UI", 10, "bold"),
    ).pack(side="left")
    tk.Button(
        top_bar,
        text="⛶ Полноэкранный режим (F11)",
        command=self.toggle_fs,
        font=("Segoe UI", 9),
    ).pack(side="right")

    tk.Label(main, text="Название теста:", font=("Segoe UI", 10, "bold")).pack(
        anchor="w"
    )
    self.ent_title = tk.Entry(main, font=("Segoe UI", 11))
    self.ent_title.pack(fill="x", pady=(0, 6))
    self.ent_title.insert(0, "Контрольная работа")
    add_context_menu(self.ent_title)

    tk.Label(
        main,
        text="Количество вопросов в варианте (из общего пула):",
        font=("Segoe UI", 10, "bold"),
    ).pack(anchor="w")
    self.ent_take = tk.Entry(main, width=6, font=("Segoe UI", 11))
    self.ent_take.pack(anchor="w", pady=(0, 8))
    self.ent_take.insert(0, str(self.test_data["take_questions"]))
    add_context_menu(self.ent_take)

    grade_frame = tk.Frame(main)
    grade_frame.pack(fill="x", pady=(0, 8))
    self.grade_ents = {}

    for g in ["5", "4", "3", "2"]:
      f = tk.Frame(grade_frame)
      f.pack(side="left", padx=8)
      tk.Label(f, text=f"{g}:").pack(side="left")
      self.grade_ents[g] = tk.Entry(f, width=5, font=("Segoe UI", 11))
      self.grade_ents[g].pack(side="left")
      self.grade_ents[g].insert(0, str(self.test_data["grading"][g]))
      add_context_menu(self.grade_ents[g])

    tk.Label(main, text="Текст вопроса:", font=("Segoe UI", 10, "bold")).pack(
        anchor="w"
    )
    self.ent_q = tk.Text(main, height=3, font=("Segoe UI", 11))
    self.ent_q.pack(fill="x", pady=(0, 6))
    add_context_menu(self.ent_q)

    type_frame = tk.Frame(main)
    type_frame.pack(fill="x", pady=(0, 6))
    tk.Label(
        type_frame, text="Тип вопроса:", font=("Segoe UI", 10, "bold")
    ).pack(side="left")
    self.qtype_var = tk.StringVar(value="Выбор ответа")
    self.type_combo = ttk.Combobox(
        type_frame,
        textvariable=self.qtype_var,
        values=["Выбор ответа", "Письменный ответ"],
        state="readonly",
        width=25,
    )
    self.type_combo.pack(side="left", padx=10)
    self.type_combo.bind("<<ComboboxSelected>>", self.on_qtype_change)

    self.dynamic_frame = tk.Frame(main)
    self.dynamic_frame.pack(fill="x", pady=(0, 6))
    self.dynamic_frame.columnconfigure(0, weight=1)

    self.choice_container = tk.Frame(self.dynamic_frame)
    self.choice_container.grid(row=0, column=0, sticky="ew")

    opts_frame = tk.Frame(self.choice_container)
    opts_frame.pack(fill="x", pady=(0, 6))
    self.opt_ents = [
        tk.Entry(opts_frame, font=("Segoe UI", 11)) for _ in range(4)
    ]
    for i, e in enumerate(self.opt_ents):
      e.pack(side="left", fill="x", expand=True, padx=(0, 5))
      e.insert(0, f"Вариант {i + 1}")
      add_context_menu(e)

    choice_correct_frame = tk.Frame(self.choice_container)
    choice_correct_frame.pack(fill="x")
    tk.Label(
        choice_correct_frame,
        text="Правильный ответ:",
        font=("Segoe UI", 10, "bold"),
    ).pack(side="left")
    self.correct_var = tk.StringVar(value="1")
    tk.OptionMenu(
        choice_correct_frame, self.correct_var, "1", "2", "3", "4"
    ).pack(side="left", padx=5)

    self.text_container = tk.Frame(self.dynamic_frame)
    self.text_container.grid(row=0, column=0, sticky="ew")
    self.text_container.grid_remove()

    tk.Label(
        self.text_container,
        text="Правильный ответ (варианты через ;):",
        font=("Segoe UI", 10, "bold"),
    ).pack(anchor="w")
    self.ent_correct_text = tk.Entry(self.text_container, font=("Segoe UI", 11))
    self.ent_correct_text.pack(fill="x")
    add_context_menu(self.ent_correct_text)

    text_settings = tk.Frame(self.text_container)
    text_settings.pack(fill="x", pady=(8, 0))

    mode_frame = tk.Frame(text_settings)
    mode_frame.pack(fill="x", pady=2)
    tk.Label(
        mode_frame, text="Проверка ответа:", font=("Segoe UI", 10, "bold")
    ).pack(side="left")

    self.check_mode_var = tk.StringVar(value="Точное совпадение")
    self.check_mode_combo = ttk.Combobox(
        mode_frame,
        textvariable=self.check_mode_var,
        values=list(CHECK_MODE_DISPLAY.values()),
        state="readonly",
        width=32,
    )
    self.check_mode_combo.pack(side="left", padx=8)

    points_frame = tk.Frame(text_settings)
    points_frame.pack(fill="x", pady=2)
    tk.Label(
        points_frame, text="Полный балл:", font=("Segoe UI", 10, "bold")
    ).pack(side="left")
    self.ent_full_points = tk.Entry(points_frame, width=6, font=("Segoe UI", 11))
    self.ent_full_points.pack(side="left", padx=(5, 15))
    self.ent_full_points.insert(0, "1")
    add_context_menu(self.ent_full_points)

    tk.Label(
        points_frame, text="Частичный балл:", font=("Segoe UI", 10, "bold")
    ).pack(side="left")
    self.ent_partial_points = tk.Entry(
        points_frame, width=6, font=("Segoe UI", 11)
    )
    self.ent_partial_points.pack(side="left", padx=5)
    self.ent_partial_points.insert(0, "0.5")
    add_context_menu(self.ent_partial_points)

    time_frame = tk.Frame(main)
    time_frame.pack(fill="x", pady=(0, 6))
    tk.Label(
        time_frame, text="Время на вопрос (сек):", font=("Segoe UI", 10, "bold")
    ).pack(side="left")
    self.ent_time = tk.Entry(time_frame, width=6, font=("Segoe UI", 11))
    self.ent_time.pack(side="left", padx=10)
    self.ent_time.insert(0, "20")
    add_context_menu(self.ent_time)

    self.btn_add = tk.Button(
        main,
        text="➕ Добавить вопрос",
        command=self.handle_question,
        font=("Segoe UI", 11, "bold"),
        bg="#4361ee",
        fg="white",
        relief="flat",
    )
    self.btn_add.pack(fill="x", pady=(5, 8))

    tk.Label(
        main, text="Добавленные вопросы:", font=("Segoe UI", 10, "bold")
    ).pack(anchor="w")
    self.listbox = tk.Listbox(
        main, height=8, font=("Segoe UI", 10), activestyle="none"
    )
    self.listbox.pack(fill="both", expand=True, pady=(0, 6))
    self.listbox.bind("<<ListboxSelect>>", self.on_select)

    ctrl_frame = tk.Frame(main)
    ctrl_frame.pack(fill="x")
    tk.Button(
        ctrl_frame, text="✏️ Изменить", command=self.edit_question, width=12
    ).pack(side="left", expand=True, fill="x", padx=2)
    tk.Button(
        ctrl_frame, text="🗑 Удалить", command=self.delete_question, width=12
    ).pack(side="left", expand=True, fill="x", padx=2)
    tk.Button(
        ctrl_frame, text="📂 Загрузить", command=self.load_test, width=12
    ).pack(side="left", expand=True, fill="x", padx=2)
    tk.Button(
        ctrl_frame,
        text="💾 Сохранить JSON",
        command=self.save_test,
        bg="#2a9d8f",
        fg="white",
        width=14,
        relief="flat",
    ).pack(side="left", expand=True, fill="x", padx=2)

  def open_ai(self):
    AIGeneratorDialog(self, self.add_ai_questions)

  def add_ai_questions(self, questions):
    self.test_data["questions"].extend(questions)
    self.refresh_list()
    messagebox.showinfo(
        "ИИ-Помощник", f"Успешно добавлено вопросов: {len(questions)}"
    )

  def on_qtype_change(self, event=None):
    if self.qtype_var.get() == "Письменный ответ":
      self.choice_container.grid_remove()
      self.text_container.grid(row=0, column=0, sticky="ew")
    else:
      self.text_container.grid_remove()
      self.choice_container.grid(row=0, column=0, sticky="ew")

  def handle_question(self):
    q_text = self.ent_q.get("1.0", "end").strip()
    try:
      time_val = int(self.ent_time.get())
    except ValueError:
      messagebox.showerror("Ошибка", "Время должно быть целым числом")
      return

    if not q_text:
      messagebox.showwarning("Внимание", "Введите текст вопроса")
      return

    q_type = "text" if self.qtype_var.get() == "Письменный ответ" else "choice"
    q_data = {"text": q_text, "type": q_type, "time": time_val}

    if q_type == "choice":
      opts = [e.get().strip() for e in self.opt_ents if e.get().strip()]
      correct = int(self.correct_var.get()) - 1
      if len(opts) < 2 or correct >= len(opts):
        messagebox.showwarning("Внимание", "Проверьте варианты ответа")
        return
      q_data["options"] = opts
      q_data["correct"] = correct
    else:
      raw_answers = self.ent_correct_text.get().strip()
      answers = [ans.strip() for ans in raw_answers.split(";") if ans.strip()]
      if not answers:
        messagebox.showwarning("Внимание", "Введите варианты правильного ответа")
        return

      check_mode = CHECK_MODE_INTERNAL.get(
          self.check_mode_var.get(), "exact"
      )
      q_data["answers"] = answers
      q_data["check_mode"] = check_mode
      q_data["full_points"] = safe_float(self.ent_full_points.get(), 1.0)
      q_data["partial_points"] = safe_float(self.ent_partial_points.get(), 0.0)

    if (
        self.editing_idx is not None
        and 0 <= self.editing_idx < len(self.test_data["questions"])
    ):
      self.test_data["questions"][self.editing_idx] = q_data
      self.editing_idx = None
      self.btn_add.config(text="➕ Добавить вопрос", bg="#4361ee")
    else:
      self.test_data["questions"].append(q_data)

    self.refresh_list()
    self.clear_form()

  def edit_question(self):
    if self.selected_idx is None:
      return
    q = self.test_data["questions"][self.selected_idx]
    self.ent_q.delete("1.0", "end")
    self.ent_q.insert("1.0", q.get("text", ""))

    q_type = q.get("type", "choice")
    self.qtype_var.set(
        "Письменный ответ" if q_type == "text" else "Выбор ответа"
    )
    self.on_qtype_change()

    if q_type == "choice":
      options = q.get("options", [])
      for i in range(4):
        self.opt_ents[i].delete(0, "end")
        if i < len(options):
          self.opt_ents[i].insert(0, options[i])
      self.correct_var.set(str(q.get("correct", 0) + 1))
    else:
      answers = get_answers_list(q)
      self.ent_correct_text.delete(0, "end")
      self.ent_correct_text.insert(0, "; ".join(answers))
      self.check_mode_var.set(
          CHECK_MODE_DISPLAY.get(
              q.get("check_mode", "exact"), "Точное совпадение"
          )
      )
      self.ent_full_points.delete(0, "end")
      self.ent_full_points.insert(0, format_number(q.get("full_points", 1.0)))
      self.ent_partial_points.delete(0, "end")
      self.ent_partial_points.insert(
          0, format_number(q.get("partial_points", 0.0))
      )

    self.ent_time.delete(0, "end")
    self.ent_time.insert(0, str(q.get("time", 20)))
    self.editing_idx = self.selected_idx
    self.btn_add.config(text="💾 Сохранить изменения", bg="#e9c46a")

  def delete_question(self):
    if self.selected_idx is not None:
      self.test_data["questions"].pop(self.selected_idx)
      self.selected_idx = None
      self.refresh_list()

  def refresh_list(self):
    self.listbox.delete(0, "end")
    for i, q in enumerate(self.test_data["questions"]):
      marker = "✍" if q.get("type") == "text" else "☑"
      self.listbox.insert(
          "end",
          f"{i + 1}. {marker} {q.get('text', '')[:45]} | ⏱ {q.get('time', 20)}с",
      )

  def on_select(self, event):
    sel = self.listbox.curselection()
    self.selected_idx = sel[0] if sel else None

  def clear_form(self):
    self.ent_q.delete("1.0", "end")
    for i, e in enumerate(self.opt_ents):
      e.delete(0, "end")
      e.insert(0, f"Вариант {i + 1}")
    self.ent_correct_text.delete(0, "end")

  def save_test(self):
    self.test_data["title"] = self.ent_title.get().strip() or "Тест"
    path = filedialog.asksaveasfilename(
        defaultextension=".json", filetypes=[("JSON", "*.json")]
    )
    if path:
      with open(path, "w", encoding="utf-8") as f:
        json.dump(self.test_data, f, ensure_ascii=False, indent=2)
      messagebox.showinfo("Успех", "Тест сохранен!")

  def load_test(self):
    path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
    if path:
      with open(path, "r", encoding="utf-8") as f:
        self.test_data = json.load(f)
      self.ent_title.delete(0, "end")
      self.ent_title.insert(0, self.test_data.get("title", "Тест"))
      self.refresh_list()


# ============================================================
# Окно ученика
# ============================================================
class StudentWindow(tk.Toplevel):

  def __init__(self, parent):
    super().__init__(parent)
    self.title("🎓 Прохождение теста")
    self.geometry("680x600")
    self.transient(parent)
    self.grab_set()
    self.toggle_fs = setup_fullscreen(self)

    self.test = None
    self.questions = []
    self.current = 0
    self.score = 0.0
    self.timer_id = None
    self.time_left = 0
    self.correct_idx = -1
    self.student = {"last_name": "", "first_name": "", "group": ""}

    self.setup_ui()

  def setup_ui(self):
    self.reg_frame = tk.Frame(self, padx=30, pady=20)
    self.reg_frame.pack(fill="both", expand=True)

    top_bar = tk.Frame(self.reg_frame)
    top_bar.pack(fill="x")
    tk.Button(
        top_bar,
        text="⛶ Полноэкранный режим (F11)",
        command=self.toggle_fs,
        font=("Segoe UI", 9),
    ).pack(side="right")

    tk.Label(
        self.reg_frame, text="Регистрация ученика", font=("Segoe UI", 18, "bold")
    ).pack(pady=(10, 20))

    tk.Label(
        self.reg_frame, text="Фамилия:", font=("Segoe UI", 11, "bold")
    ).pack(anchor="w")
    self.ent_last = tk.Entry(self.reg_frame, font=("Segoe UI", 12))
    self.ent_last.pack(fill="x", pady=(0, 10))
    add_context_menu(self.ent_last)

    tk.Label(self.reg_frame, text="Имя:", font=("Segoe UI", 11, "bold")).pack(
        anchor="w"
    )
    self.ent_first = tk.Entry(self.reg_frame, font=("Segoe UI", 12))
    self.ent_first.pack(fill="x", pady=(0, 10))
    add_context_menu(self.ent_first)

    tk.Label(
        self.reg_frame, text="Номер группы:", font=("Segoe UI", 11, "bold")
    ).pack(anchor="w")
    self.ent_group = tk.Entry(self.reg_frame, font=("Segoe UI", 12))
    self.ent_group.pack(fill="x", pady=(0, 20))
    add_context_menu(self.ent_group)

    tk.Button(
        self.reg_frame,
        text="📂 Выбрать тест и начать",
        command=self.load_test,
        font=("Segoe UI", 13, "bold"),
        bg="#4361ee",
        fg="white",
        relief="flat",
    ).pack(pady=10, fill="x")

    self.test_frame = tk.Frame(self, padx=20, pady=10)
    self.lbl_title = tk.Label(
        self.test_frame, text="", font=("Segoe UI", 15, "bold")
    )
    self.lbl_title.pack(pady=(10, 5))

    self.lbl_timer = tk.Label(
        self.test_frame,
        text="⏱ 00:00",
        font=("Segoe UI", 20, "bold"),
        fg="#e63946",
    )
    self.lbl_timer.pack()

    self.lbl_q = tk.Label(
        self.test_frame,
        text="",
        wraplength=560,
        font=("Segoe UI", 13),
        justify="left",
    )
    self.lbl_q.pack(pady=10)

    self.answer_area = tk.Frame(self.test_frame)
    self.answer_area.pack(fill="x", pady=5)

    self.opts_frame = tk.Frame(self.answer_area)
    self.opts_frame.pack(fill="x")
    self.answer_var = tk.StringVar(value="-1")
    self.opt_btns = []

    for i in range(4):
      rb = tk.Radiobutton(
          self.opts_frame,
          text="",
          variable=self.answer_var,
          value=str(i),
          font=("Segoe UI", 12),
          anchor="w",
          indicatoron=False,
          width=55,
          bg="white",
      )
      rb.pack(pady=4, fill="x")
      self.opt_btns.append(rb)

    self.text_frame = tk.Frame(self.answer_area)
    self.lbl_text_answer = tk.Label(
        self.text_frame, text="Введите ответ:", font=("Segoe UI", 11, "bold")
    )
    self.lbl_text_answer.pack(anchor="w")

    self.answer_entry_var = tk.StringVar()
    self.ent_answer = tk.Entry(
        self.text_frame,
        textvariable=self.answer_entry_var,
        font=("Segoe UI", 13),
    )
    self.ent_answer.pack(fill="x", ipady=6)
    add_context_menu(self.ent_answer)

    self.btn_next = tk.Button(
        self.test_frame,
        text="Далее →",
        command=self.next_q,
        font=("Segoe UI", 13, "bold"),
        bg="#2a9d8f",
        fg="white",
        relief="flat",
    )
    self.btn_next.pack(pady=15)

  def load_test(self):
    if (
        not self.ent_last.get().strip()
        or not self.ent_first.get().strip()
        or not self.ent_group.get().strip()
    ):
      messagebox.showwarning("Внимание", "Заполните все данные о себе")
      return

    path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
    if not path:
      return

    with open(path, "r", encoding="utf-8") as f:
      self.test = json.load(f)

    questions = copy.deepcopy(self.test.get("questions", []))
    random.shuffle(questions)
    self.questions = questions[: self.test.get("take_questions", len(questions))]
    self.student = {
        "last_name": self.ent_last.get().strip(),
        "first_name": self.ent_first.get().strip(),
        "group": self.ent_group.get().strip(),
    }

    self.reg_frame.pack_forget()
    self.test_frame.pack(fill="both", expand=True)
    self.show_q()

  def show_q(self):
    if self.timer_id:
      self.after_cancel(self.timer_id)

    if self.current >= len(self.questions):
      self.finish()
      return

    q = self.questions[self.current]
    q_type = q.get("type", "choice")

    self.lbl_title.config(text=f"📝 {self.test.get('title', 'Тест')}")
    self.lbl_q.config(text=q.get("text", ""))

    if q_type == "text":
      self.opts_frame.pack_forget()
      self.text_frame.pack(fill="x")
      mode = q.get("check_mode", "exact")
      hint = (
          "Введите пропущенную букву или пропуск (-):"
          if mode == "dash"
          else "Введите ответ:"
      )
      self.lbl_text_answer.config(text=hint)
      self.answer_entry_var.set("")
    else:
      self.text_frame.pack_forget()
      self.opts_frame.pack(fill="x")
      self.answer_var.set("-1")
      options = q.get("options", [])
      correct = q.get("correct", 0)
      pairs = [(options[i], i == correct) for i in range(len(options))]
      random.shuffle(pairs)
      self.correct_idx = next(
          (i for i, (_, is_c) in enumerate(pairs) if is_c), -1
      )

      for i, rb in enumerate(self.opt_btns):
        if i < len(pairs):
          rb.config(text=f"{i + 1}. {pairs[i][0]}", state="normal")
        else:
          rb.config(text="", state="disabled")

    self.time_left = int(q.get("time", 20))
    self.update_timer()

  def update_timer(self):
    m, s = divmod(max(self.time_left, 0), 60)
    self.lbl_timer.config(text=f"⏱ {m:02d}:{s:02d}")
    if self.time_left > 0:
      self.time_left -= 1
      self.timer_id = self.after(1000, self.update_timer)
    else:
      self.next_q()

  def next_q(self):
    if self.current < len(self.questions):
      q = self.questions[self.current]
      if q.get("type") == "text":
        self.score += score_text_question(q, self.answer_entry_var.get())
      else:
        if self.answer_var.get() == str(self.correct_idx):
          self.score += 1.0

    self.current += 1
    self.show_q()

  def finish(self):
    if self.timer_id:
      self.after_cancel(self.timer_id)

    total = sum(get_question_max_points(q) for q in self.questions)
    grading = self.test.get("grading", {}) if self.test else {}

    grade = "2"
    if self.score >= safe_float(grading.get("5", 0)):
      grade = "5"
    elif self.score >= safe_float(grading.get("4", 0)):
      grade = "4"
    elif self.score >= safe_float(grading.get("3", 0)):
      grade = "3"

    now = datetime.now()
    record = {
        "last_name": self.student.get("last_name", ""),
        "first_name": self.student.get("first_name", ""),
        "group": self.student.get("group", ""),
        "test": self.test.get("title", "Без названия")
        if self.test
        else "Без названия",
        "score": round(self.score, 2),
        "total": round(total, 2),
        "grade": grade,
        "date": now.strftime("%d.%m.%Y %H:%M"),
        "timestamp": now.timestamp(),
    }
    append_statistics(record)

    for w in self.winfo_children():
      w.destroy()
    tk.Label(
        self, text="✅ Тест завершён!", font=("Segoe UI", 20, "bold")
    ).pack(pady=30)
    tk.Label(
        self,
        text=f"Результат: {format_number(self.score)} из {format_number(total)}",
        font=("Segoe UI", 16),
    ).pack(pady=5)
    tk.Label(
        self,
        text=f"Оценка: {grade}",
        font=("Segoe UI", 26, "bold"),
        fg="#2a9d8f",
    ).pack(pady=15)
    tk.Button(
        self, text="Закрыть", command=self.destroy, font=("Segoe UI", 12)
    ).pack(pady=20)


# ============================================================
# Окно статистики
# ============================================================
class StatsWindow(tk.Toplevel):

  def __init__(self, parent):
    super().__init__(parent)
    self.title("📊 Статистика")
    self.geometry("1100x560")
    self.transient(parent)
    self.grab_set()
    self.toggle_fs = setup_fullscreen(self)

    self.stats = []
    self.setup_ui()
    self.refresh()

  def setup_ui(self):
    top = tk.Frame(self, padx=12, pady=10)
    top.pack(fill="x")

    top_bar = tk.Frame(top)
    top_bar.pack(fill="x")
    tk.Label(
        top_bar,
        text="Статистика прохождения тестов",
        font=("Segoe UI", 16, "bold"),
    ).pack(side="left")
    tk.Button(
        top_bar,
        text="⛶ Полноэкранный режим (F11)",
        command=self.toggle_fs,
        font=("Segoe UI", 9),
    ).pack(side="right")

    table = tk.Frame(self, padx=12)
    table.pack(fill="both", expand=True)

    columns = ("last", "first", "group", "test", "date", "score", "grade")
    self.tree = ttk.Treeview(
        table, columns=columns, show="headings", selectmode="extended"
    )

    headings = [
        ("last", "Фамилия", 120),
        ("first", "Имя", 120),
        ("group", "Группа", 90),
        ("test", "Название теста", 260),
        ("date", "Дата и время", 140),
        ("score", "Баллы", 100),
        ("grade", "Оценка", 70),
    ]

    for col, text, width in headings:
      self.tree.heading(col, text=text)
      self.tree.column(col, width=width, anchor="w")

    vsb = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
    self.tree.configure(yscrollcommand=vsb.set)
    self.tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")

    table.rowconfigure(0, weight=1)
    table.columnconfigure(0, weight=1)

    bottom = tk.Frame(self, padx=12, pady=10)
    bottom.pack(fill="x")
    tk.Button(
        bottom,
        text="🗑 Удалить выбранную запись",
        command=self.delete_selected,
    ).pack(side="left")
    tk.Button(bottom, text="Закрыть", command=self.destroy).pack(side="right")

  def refresh(self):
    self.stats = load_statistics()
    for item in self.tree.get_children():
      self.tree.delete(item)

    for idx, rec in enumerate(self.stats):
      score_display = (
          f"{format_number(rec.get('score', 0))}/{format_number(rec.get('total', 0))}"
      )
      self.tree.insert(
          "",
          "end",
          iid=str(idx),
          values=(
              rec.get("last_name", ""),
              rec.get("first_name", ""),
              rec.get("group", ""),
              rec.get("test", "Без названия"),
              rec.get("date", ""),
              score_display,
              rec.get("grade", ""),
          ),
      )

  def delete_selected(self):
    selected = self.tree.selection()
    if not selected:
      return

    indexes = sorted([int(x) for x in selected], reverse=True)
    for idx in indexes:
      if 0 <= idx < len(self.stats):
        self.stats.pop(idx)

    save_statistics(self.stats)
    self.refresh()


# ============================================================
# Запуск программы
# ============================================================
if __name__ == "__main__":
  app = TestApp()
  app.root.mainloop()
