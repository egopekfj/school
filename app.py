import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import random
import copy
import os
from datetime import datetime


# ============================================================
# Файл статистики
# ============================================================
STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_statistics.json")


# ============================================================
# Режимы проверки письменных ответов
# ============================================================
CHECK_MODE_DISPLAY = {
    "exact": "Точное совпадение",
    "contains": "Содержит правильный ответ",
    "letter": "Только пропущенная буква"
}

CHECK_MODE_INTERNAL = {v: k for k, v in CHECK_MODE_DISPLAY.items()}


# ============================================================
# Вспомогательные функции
# ============================================================
def safe_float(value, default=0.0):
    """Безопасное преобразование в float."""
    if value is None:
        return default

    try:
        if isinstance(value, str):
            value = value.replace(",", ".")
        return float(value)
    except Exception:
        return default


def format_number(value):
    """Красивый вывод чисел: 5 вместо 5.0, 2.5 вместо 2.50."""
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
    """Загрузка статистики из JSON-файла."""
    if not os.path.exists(STATS_FILE):
        return []

    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_statistics(stats):
    """Сохранение статистики в JSON-файл."""
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def append_statistics(record):
    """Добавление одной записи в статистику."""
    stats = load_statistics()
    stats.append(record)
    save_statistics(stats)


def normalize_answer(text):
    """
    Нормализация ответа для сравнения.
    Пример: "  Москва! " -> "москва"
    """
    if not isinstance(text, str):
        text = str(text)

    text = text.strip().lower().replace("ё", "е")

    # Убираем часть знаков препинания
    for ch in ".,!?;:()[]{}\"'«»":
        text = text.replace(ch, "")

    # Убираем лишние пробелы
    text = " ".join(text.split())

    return text


def get_answers_list(q):
    """Получает список правильных ответов из вопроса."""
    answers = q.get("answers", [])

    if isinstance(answers, str):
        answers = [
            ans.strip()
            for ans in answers.split(";")
            if ans.strip()
        ]

    elif isinstance(answers, list):
        answers = [
            str(ans).strip()
            for ans in answers
            if str(ans).strip()
        ]

    else:
        answers = []

    # Поддержка возможного старого поля correct_text
    if not answers and q.get("correct_text"):
        raw = str(q.get("correct_text"))
        answers = [
            ans.strip()
            for ans in raw.split(";")
            if ans.strip()
        ]

    return answers


def contains_correct_answer(user_answer, accepted_answers):
    """
    Проверяет, содержит ли ответ ученика правильный ответ.
    Если правильный ответ - одно слово, ищем как отдельное слово.
    Если правильный ответ - фраза, ищем как подстроку.
    """
    user_norm = normalize_answer(user_answer)

    if not user_norm:
        return False

    user_tokens = set(user_norm.split())

    for accepted in accepted_answers:
        acc_norm = normalize_answer(accepted)

        if not acc_norm:
            continue

        if " " in acc_norm:
            # Фраза
            if acc_norm in user_norm:
                return True
        else:
            # Одно слово / буква / число
            if acc_norm in user_tokens:
                return True

    return False


def contains_any_correct_word(user_answer, accepted_answers):
    """
    Проверяет, есть ли в ответе ученика хотя бы одно правильное слово
    из правильных ответов.
    Используется для частичного балла.
    """
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


def extract_letters(text):
    """Извлекает буквы из текста после нормализации."""
    return [ch for ch in normalize_answer(text) if ch.isalpha()]


def letter_answer_is_correct(user_answer, accepted_answers):
    """
    Режим 'Только пропущенная буква'.
    Полный балл, если введена ровно одна правильная буква.
    """
    user_letters = extract_letters(user_answer)

    # Требуем именно отдельную букву
    if len(user_letters) != 1:
        return False

    user_letter = user_letters[0]

    for accepted in accepted_answers:
        acc_letters = extract_letters(accepted)

        if not acc_letters:
            continue

        # Если учитель случайно написал слово, берём первую букву
        if user_letter == acc_letters[0]:
            return True

    return False


def letter_answer_contains(user_answer, accepted_answers):
    """
    Частичная проверка для буквы:
    правильная буква где-то встречается в ответе ученика.
    """
    user_letters = set(extract_letters(user_answer))

    if not user_letters:
        return False

    for accepted in accepted_answers:
        acc_letters = extract_letters(accepted)

        if not acc_letters:
            continue

        if acc_letters[0] in user_letters:
            return True

    return False


def exact_answer_is_correct(user_answer, accepted_answers):
    """Точное совпадение ответа ученика с одним из правильных ответов."""
    user_norm = normalize_answer(user_answer)

    if not user_norm:
        return False

    for accepted in accepted_answers:
        if user_norm == normalize_answer(accepted):
            return True

    return False


def get_question_max_points(q):
    """Максимальный балл за вопрос."""
    if q.get("type") == "text":
        points = safe_float(q.get("full_points", 1.0), 1.0)
        return max(0.0, points)

    # Обычный вопрос с выбором ответа
    return 1.0


def score_text_question(q, user_answer):
    """Подсчёт баллов за письменный вопрос."""
    answers = get_answers_list(q)

    full_points = safe_float(q.get("full_points", 1.0), 1.0)
    partial_points = safe_float(q.get("partial_points", 0.0), 0.0)

    if full_points < 0:
        full_points = 0.0

    if partial_points < 0:
        partial_points = 0.0

    if partial_points > full_points:
        partial_points = full_points

    if not user_answer or not str(user_answer).strip():
        return 0.0

    mode = q.get("check_mode", "exact")

    # Режим: содержит правильный ответ
    if mode == "contains":
        if contains_correct_answer(user_answer, answers):
            return full_points

        if partial_points > 0 and contains_any_correct_word(user_answer, answers):
            return partial_points

        return 0.0

    # Режим: только пропущенная буква
    if mode == "letter":
        if letter_answer_is_correct(user_answer, answers):
            return full_points

        if partial_points > 0 and letter_answer_contains(user_answer, answers):
            return partial_points

        return 0.0

    # Режим: точное совпадение
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
        self.root.geometry("560x480")
        self.root.resizable(False, False)
        self.setup_menu()

    def setup_menu(self):
        for w in self.root.winfo_children():
            w.destroy()

        tk.Label(
            self.root,
            text="Выберите режим работы:",
            font=("Segoe UI", 18, "bold")
        ).pack(pady=(40, 10))

        tk.Button(
            self.root,
            text="👨‍🏫 Конструктор тестов (Учитель)",
            command=self.open_teacher,
            height=2,
            font=("Segoe UI", 13),
            bg="#4361ee",
            fg="white",
            relief="flat"
        ).pack(pady=10, padx=50, fill="x")

        tk.Button(
            self.root,
            text="🎓 Пройти тест (Ученик)",
            command=self.open_student,
            height=2,
            font=("Segoe UI", 13),
            bg="#2a9d8f",
            fg="white",
            relief="flat"
        ).pack(pady=10, padx=50, fill="x")

        tk.Button(
            self.root,
            text="📊 Статистика",
            command=self.open_statistics,
            height=2,
            font=("Segoe UI", 13),
            bg="#f4a261",
            fg="white",
            relief="flat"
        ).pack(pady=10, padx=50, fill="x")

        tk.Label(
            self.root,
            text="Оффлайн • Таймер • Выбор ответа • Письменный ответ • Частичный балл • Статистика",
            fg="gray",
            font=("Segoe UI", 9)
        ).pack(pady=20)

    def open_teacher(self):
        TeacherWindow(self.root)

    def open_student(self):
        StudentWindow(self.root)

    def open_statistics(self):
        StatsWindow(self.root)


# ============================================================
# Окно учителя
# ============================================================
class TeacherWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("🛠 Конструктор тестов")
        self.geometry("920x900")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        self.lift()

        self.test_data = {
            "title": "Новый тест",
            "take_questions": 5,
            "grading": {
                "5": 18,
                "4": 14,
                "3": 9,
                "2": 0
            },
            "questions": []
        }

        self.selected_idx = None
        self.editing_idx = None
        self.setup_ui()

    def setup_ui(self):
        main = tk.Frame(self, padx=15, pady=10)
        main.pack(fill=tk.BOTH, expand=True)

        # 1. Название теста
        tk.Label(
            main,
            text="Название теста:",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        self.ent_title = tk.Entry(main, font=("Segoe UI", 11))
        self.ent_title.pack(fill="x", pady=(0, 6))
        self.ent_title.insert(0, "Контрольная работа")

        # 2. Сколько вопросов выдавать ученику
        tk.Label(
            main,
            text="Количество вопросов в варианте (из общего пула):",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        self.ent_take = tk.Entry(main, width=6, font=("Segoe UI", 11))
        self.ent_take.pack(anchor="w", pady=(0, 8))
        self.ent_take.insert(0, str(self.test_data["take_questions"]))

        tk.Label(
            main,
            text="💡 При каждом запуске ученик получит случайные вопросы из вашего пула",
            fg="#666",
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(0, 6))

        # 3. Критерии оценок
        tk.Label(
            main,
            text="Мин. баллов для оценок (5 / 4 / 3 / 2):",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

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

        # 4. Текст вопроса
        tk.Label(
            main,
            text="Текст вопроса:",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        self.ent_q = tk.Text(main, height=3, font=("Segoe UI", 11))
        self.ent_q.pack(fill="x", pady=(0, 6))

        # 5. Тип вопроса
        type_frame = tk.Frame(main)
        type_frame.pack(fill="x", pady=(0, 6))

        tk.Label(
            type_frame,
            text="Тип вопроса:",
            font=("Segoe UI", 10, "bold")
        ).pack(side="left")

        self.qtype_var = tk.StringVar(value="Выбор ответа")

        self.type_combo = ttk.Combobox(
            type_frame,
            textvariable=self.qtype_var,
            values=["Выбор ответа", "Письменный ответ"],
            state="readonly",
            width=25
        )
        self.type_combo.pack(side="left", padx=10)
        self.type_combo.bind("<<ComboboxSelected>>", self.on_qtype_change)

        # 6. Динамическая область: выбор ответа или письменный ответ
        self.dynamic_frame = tk.Frame(main)
        self.dynamic_frame.pack(fill="x", pady=(0, 6))
        self.dynamic_frame.columnconfigure(0, weight=1)

        # Блок для вопроса с выбором ответа
        self.choice_container = tk.Frame(self.dynamic_frame)
        self.choice_container.grid(row=0, column=0, sticky="ew")

        tk.Label(
            self.choice_container,
            text="Варианты ответов:",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        opts_frame = tk.Frame(self.choice_container)
        opts_frame.pack(fill="x", pady=(0, 6))

        self.opt_ents = [tk.Entry(opts_frame, font=("Segoe UI", 11)) for _ in range(4)]

        for i, e in enumerate(self.opt_ents):
            e.pack(side="left", fill="x", expand=True, padx=(0, 5))
            e.insert(0, f"Вариант {i + 1}")

        choice_correct_frame = tk.Frame(self.choice_container)
        choice_correct_frame.pack(fill="x")

        tk.Label(
            choice_correct_frame,
            text="Правильный ответ:",
            font=("Segoe UI", 10, "bold")
        ).pack(side="left")

        self.correct_var = tk.StringVar(value="1")
        tk.OptionMenu(
            choice_correct_frame,
            self.correct_var,
            "1", "2", "3", "4"
        ).pack(side="left", padx=5)

        # Блок для письменного ответа
        self.text_container = tk.Frame(self.dynamic_frame)
        self.text_container.grid(row=0, column=0, sticky="ew")
        self.text_container.grid_remove()

        tk.Label(
            self.text_container,
            text="Правильный ответ (несколько вариантов через ;):",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        self.ent_correct_text = tk.Entry(self.text_container, font=("Segoe UI", 11))
        self.ent_correct_text.pack(fill="x")

        tk.Label(
            self.text_container,
            text="Например: А; а   или:   Москва; город Москва",
            fg="#666",
            font=("Segoe UI", 9)
        ).pack(anchor="w")

        # Настройки проверки письменного ответа
        text_settings = tk.Frame(self.text_container)
        text_settings.pack(fill="x", pady=(8, 0))

        mode_frame = tk.Frame(text_settings)
        mode_frame.pack(fill="x", pady=2)

        tk.Label(
            mode_frame,
            text="Проверка ответа:",
            font=("Segoe UI", 10, "bold")
        ).pack(side="left")

        self.check_mode_var = tk.StringVar(value="Точное совпадение")

        self.check_mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.check_mode_var,
            values=list(CHECK_MODE_DISPLAY.values()),
            state="readonly",
            width=32
        )
        self.check_mode_combo.pack(side="left", padx=8)

        points_frame = tk.Frame(text_settings)
        points_frame.pack(fill="x", pady=2)

        tk.Label(
            points_frame,
            text="Баллы за полный ответ:",
            font=("Segoe UI", 10, "bold")
        ).pack(side="left")

        self.ent_full_points = tk.Entry(points_frame, width=6, font=("Segoe UI", 11))
        self.ent_full_points.pack(side="left", padx=(5, 15))
        self.ent_full_points.insert(0, "1")

        tk.Label(
            points_frame,
            text="Частичный балл:",
            font=("Segoe UI", 10, "bold")
        ).pack(side="left")

        self.ent_partial_points = tk.Entry(points_frame, width=6, font=("Segoe UI", 11))
        self.ent_partial_points.pack(side="left", padx=5)
        self.ent_partial_points.insert(0, "0.5")

        tk.Label(
            self.text_container,
            text=(
                "Частичный балл начисляется, если ответ содержит правильный фрагмент/слово/букву, "
                "но не совпадает полностью. 0 — отключить."
            ),
            fg="#666",
            font=("Segoe UI", 8),
            wraplength=560,
            justify="left"
        ).pack(anchor="w")

        # 7. Время на вопрос
        time_frame = tk.Frame(main)
        time_frame.pack(fill="x", pady=(0, 6))

        tk.Label(
            time_frame,
            text="Время на вопрос (сек):",
            font=("Segoe UI", 10, "bold")
        ).pack(side="left")

        self.ent_time = tk.Entry(time_frame, width=6, font=("Segoe UI", 11))
        self.ent_time.pack(side="left", padx=10)
        self.ent_time.insert(0, "20")

        # 8. Кнопка добавления/сохранения вопроса
        self.btn_add = tk.Button(
            main,
            text="➕ Добавить вопрос",
            command=self.handle_question,
            font=("Segoe UI", 11, "bold"),
            bg="#4361ee",
            fg="white",
            relief="flat"
        )
        self.btn_add.pack(fill="x", pady=(5, 8))

        # 9. Список вопросов
        tk.Label(
            main,
            text="Добавленные вопросы:",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        self.listbox = tk.Listbox(
            main,
            height=9,
            font=("Segoe UI", 10),
            activestyle="none"
        )
        self.listbox.pack(fill="both", expand=True, pady=(0, 6))
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # 10. Предпросмотр
        tk.Button(
            main,
            text="👁 Предпросмотр теста",
            command=self.preview_test,
            bg="#f4a261",
            fg="white",
            relief="flat"
        ).pack(fill="x", pady=(0, 6))

        # 11. Управление тестом
        ctrl_frame = tk.Frame(main)
        ctrl_frame.pack(fill="x")

        tk.Button(
            ctrl_frame,
            text="✏️ Изменить",
            command=self.edit_question,
            width=12
        ).pack(side="left", expand=True, fill="x", padx=2)

        tk.Button(
            ctrl_frame,
            text="🗑 Удалить",
            command=self.delete_question,
            width=12
        ).pack(side="left", expand=True, fill="x", padx=2)

        tk.Button(
            ctrl_frame,
            text="📂 Загрузить",
            command=self.load_test,
            width=12
        ).pack(side="left", expand=True, fill="x", padx=2)

        tk.Button(
            ctrl_frame,
            text="💾 Сохранить JSON",
            command=self.save_test,
            bg="#2a9d8f",
            fg="white",
            width=14,
            relief="flat"
        ).pack(side="left", expand=True, fill="x", padx=2)

    def on_qtype_change(self, event=None):
        """Переключение интерфейса в зависимости от типа вопроса."""
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

        q_type_display = self.qtype_var.get()
        q_type = "text" if q_type_display == "Письменный ответ" else "choice"

        q_data = {
            "text": q_text,
            "type": q_type,
            "time": time_val
        }

        if q_type == "choice":
            opts = [e.get().strip() for e in self.opt_ents if e.get().strip()]

            try:
                correct = int(self.correct_var.get()) - 1
            except ValueError:
                correct = -1

            if len(opts) < 2:
                messagebox.showwarning("Внимание", "Добавьте минимум 2 варианта ответа")
                return

            if correct < 0 or correct >= len(opts):
                messagebox.showwarning(
                    "Внимание",
                    "Номер правильного ответа больше количества вариантов"
                )
                return

            q_data["options"] = opts
            q_data["correct"] = correct

        else:
            raw_answers = self.ent_correct_text.get().strip()

            if not raw_answers:
                messagebox.showwarning(
                    "Внимание",
                    "Введите правильный ответ для письменного вопроса"
                )
                return

            answers = [
                ans.strip()
                for ans in raw_answers.split(";")
                if ans.strip()
            ]

            if not answers:
                messagebox.showwarning(
                    "Внимание",
                    "Введите хотя бы один правильный ответ"
                )
                return

            check_mode = CHECK_MODE_INTERNAL.get(
                self.check_mode_var.get(),
                "exact"
            )

            full_points = safe_float(self.ent_full_points.get(), 1.0)
            partial_points = safe_float(self.ent_partial_points.get(), 0.0)

            if full_points < 0:
                full_points = 0.0

            if partial_points < 0:
                partial_points = 0.0

            if partial_points > full_points:
                partial_points = full_points

            q_data["answers"] = answers
            q_data["check_mode"] = check_mode
            q_data["full_points"] = full_points
            q_data["partial_points"] = partial_points

        if self.editing_idx is not None and 0 <= self.editing_idx < len(self.test_data["questions"]):
            self.test_data["questions"][self.editing_idx] = q_data
            self.editing_idx = None
            self.btn_add.config(text="➕ Добавить вопрос", bg="#4361ee")
            messagebox.showinfo("Успех", "Вопрос обновлён!")
        else:
            self.test_data["questions"].append(q_data)
            messagebox.showinfo("Успех", "Вопрос добавлен!")

        self.refresh_list()
        self.clear_form()

    def edit_question(self):
        if self.selected_idx is None:
            messagebox.showinfo(
                "Инфо",
                "Выберите вопрос из списка для редактирования"
            )
            return

        q = self.test_data["questions"][self.selected_idx]

        self.ent_q.delete("1.0", "end")
        self.ent_q.insert("1.0", q.get("text", ""))

        q_type = q.get("type", "choice")

        if q_type == "text":
            self.qtype_var.set("Письменный ответ")
        else:
            self.qtype_var.set("Выбор ответа")

        self.on_qtype_change()

        # Заполняем поля для выбора ответа
        options = q.get("options", [])

        for i in range(4):
            self.opt_ents[i].delete(0, "end")

            if i < len(options):
                self.opt_ents[i].insert(0, options[i])
            else:
                self.opt_ents[i].insert(0, f"Вариант {i + 1}")

        self.correct_var.set(str(q.get("correct", 0) + 1))

        # Заполняем поле для письменного ответа
        answers = get_answers_list(q)

        self.ent_correct_text.delete(0, "end")
        self.ent_correct_text.insert(0, "; ".join(answers))

        check_mode = q.get("check_mode", "exact")
        self.check_mode_var.set(
            CHECK_MODE_DISPLAY.get(check_mode, "Точное совпадение")
        )

        self.ent_full_points.delete(0, "end")
        self.ent_full_points.insert(0, format_number(q.get("full_points", 1.0)))

        self.ent_partial_points.delete(0, "end")
        self.ent_partial_points.insert(0, format_number(q.get("partial_points", 0.0)))

        self.ent_time.delete(0, "end")
        self.ent_time.insert(0, str(q.get("time", 20)))

        self.editing_idx = self.selected_idx
        self.btn_add.config(text="💾 Сохранить изменения", bg="#e9c46a")

    def delete_question(self):
        if self.selected_idx is None:
            messagebox.showinfo("Инфо", "Выберите вопрос для удаления")
            return

        if messagebox.askyesno("Подтверждение", "Удалить выбранный вопрос?"):
            self.test_data["questions"].pop(self.selected_idx)

            self.editing_idx = None
            self.selected_idx = None
            self.btn_add.config(text="➕ Добавить вопрос", bg="#4361ee")

            self.refresh_list()

    def refresh_list(self):
        self.listbox.delete(0, "end")

        for i, q in enumerate(self.test_data["questions"]):
            text = q.get("text", "")
            time_q = q.get("time", 0)
            q_type = q.get("type", "choice")

            marker = "✍" if q_type == "text" else "☑"
            points = format_number(get_question_max_points(q))

            display_text = text[:45] + ("..." if len(text) > 45 else "")
            self.listbox.insert(
                "end",
                f"{i + 1}. {marker} {display_text} | ⏱ {time_q} с | {points} б."
            )

        self.listbox.selection_clear(0, "end")

    def on_select(self, event):
        sel = self.listbox.curselection()
        self.selected_idx = sel[0] if sel else None

    def clear_form(self):
        self.ent_q.delete("1.0", "end")

        for i, e in enumerate(self.opt_ents):
            e.delete(0, "end")
            e.insert(0, f"Вариант {i + 1}")

        self.correct_var.set("1")

        self.ent_correct_text.delete(0, "end")

        self.ent_time.delete(0, "end")
        self.ent_time.insert(0, "20")

        self.ent_full_points.delete(0, "end")
        self.ent_full_points.insert(0, "1")

        self.ent_partial_points.delete(0, "end")
        self.ent_partial_points.insert(0, "0.5")

        self.listbox.selection_clear(0, "end")

    def update_test_metadata(self):
        """Обновляет название, количество вопросов и критерии оценок."""
        self.test_data["title"] = self.ent_title.get().strip() or "Тест"

        total_q = len(self.test_data.get("questions", []))

        try:
            take_val = int(self.ent_take.get())

            if take_val <= 0:
                take_val = total_q
            elif take_val > total_q:
                messagebox.showinfo(
                    "Коррекция",
                    f"В пуле всего {total_q} вопросов. Будет выдаваться {total_q}."
                )
                take_val = total_q

            self.test_data["take_questions"] = take_val

        except ValueError:
            self.test_data["take_questions"] = total_q

        if "grading" not in self.test_data or not isinstance(self.test_data["grading"], dict):
            self.test_data["grading"] = {"5": 0, "4": 0, "3": 0, "2": 0}

        for g in ["5", "4", "3", "2"]:
            current = self.test_data["grading"].get(g, 0)
            self.test_data["grading"][g] = safe_float(self.grade_ents[g].get(), current)

    def preview_test(self):
        """Открывает предпросмотр теста."""
        self.update_test_metadata()

        if not self.test_data.get("questions"):
            messagebox.showwarning("Внимание", "Добавьте хотя бы один вопрос")
            return

        PreviewWindow(self, self.test_data, can_save=True)

    def save_test(self):
        """
        Сохранение теперь идёт через предпросмотр:
        пользователь сначала видит тест, затем сохраняет JSON.
        """
        self.preview_test()

    def load_test(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json")]
        )

        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                raise ValueError("Неверный формат файла теста")

            if "questions" not in data or not isinstance(data["questions"], list):
                data["questions"] = []

            if "grading" not in data or not isinstance(data["grading"], dict):
                data["grading"] = {"5": 0, "4": 0, "3": 0, "2": 0}

            self.test_data = data

            self.ent_title.delete(0, "end")
            self.ent_title.insert(0, self.test_data.get("title", "Тест"))

            self.ent_take.delete(0, "end")
            self.ent_take.insert(
                0,
                str(self.test_data.get("take_questions", len(self.test_data["questions"])))
            )

            for g in ["5", "4", "3", "2"]:
                self.grade_ents[g].delete(0, "end")
                self.grade_ents[g].insert(
                    0,
                    format_number(self.test_data.get("grading", {}).get(g, 0))
                )

            self.editing_idx = None
            self.selected_idx = None
            self.btn_add.config(text="➕ Добавить вопрос", bg="#4361ee")

            self.refresh_list()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл:\n{e}")


# ============================================================
# Окно предпросмотра теста
# ============================================================
class PreviewWindow(tk.Toplevel):
    def __init__(self, parent, test_data, can_save=True):
        super().__init__(parent)
        self.test_data = copy.deepcopy(test_data)
        self.can_save = can_save

        self.title("👁 Предпросмотр теста")
        self.geometry("780x680")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        self.lift()

        self.setup_ui()

    def setup_ui(self):
        top = tk.Frame(self)
        top.pack(fill="both", expand=True, padx=10, pady=10)

        text = tk.Text(
            top,
            wrap="word",
            font=("Segoe UI", 10),
            padx=10,
            pady=10
        )

        vsb = ttk.Scrollbar(top, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=vsb.set)

        text.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        text.insert("1.0", self.build_preview_text())
        text.config(state="disabled")

        bottom = tk.Frame(self)
        bottom.pack(fill="x", padx=10, pady=8)

        if self.can_save:
            tk.Button(
                bottom,
                text="💾 Сохранить JSON",
                command=self.save_json,
                bg="#2a9d8f",
                fg="white",
                relief="flat"
            ).pack(side="left")

        tk.Button(
            bottom,
            text="Закрыть",
            command=self.destroy
        ).pack(side="right")

    def build_preview_text(self):
        data = self.test_data
        questions = data.get("questions", [])
        grading = data.get("grading", {})

        lines = []
        lines.append("ПРЕДПРОСМОТР ТЕСТА")
        lines.append("=" * 45)
        lines.append(f"Название теста: {data.get('title', 'Тест')}")
        lines.append(f"Всего вопросов в пуле: {len(questions)}")
        lines.append(f"Ученику будет выдано: {data.get('take_questions', len(questions))}")
        lines.append("")
        lines.append("Критерии оценок:")

        for mark in ["5", "4", "3", "2"]:
            lines.append(f"   Оценка {mark}: от {format_number(grading.get(mark, 0))} баллов")

        lines.append("")
        lines.append("ВОПРОСЫ:")
        lines.append("-" * 45)
        lines.append("")

        for i, q in enumerate(questions, 1):
            q_type = q.get("type", "choice")
            type_name = "Письменный ответ" if q_type == "text" else "Выбор ответа"

            lines.append(f"{i}. [{type_name}] {q.get('text', '')}")
            lines.append(f"   Время: {q.get('time', 20)} с")

            if q_type == "text":
                answers = get_answers_list(q)
                mode = CHECK_MODE_DISPLAY.get(
                    q.get("check_mode", "exact"),
                    "Точное совпадение"
                )

                lines.append(f"   Проверка: {mode}")
                lines.append(
                    f"   Правильные ответы: {'; '.join(answers) if answers else 'не заданы'}"
                )
                lines.append(
                    f"   Баллы: полный {format_number(q.get('full_points', 1.0))}, "
                    f"частичный {format_number(q.get('partial_points', 0.0))}"
                )

            else:
                options = q.get("options", [])
                correct = q.get("correct", -1)

                try:
                    correct = int(correct)
                except Exception:
                    correct = -1

                if options:
                    lines.append("   Варианты:")
                    for j, opt in enumerate(options):
                        lines.append(f"      {j + 1}) {opt}")
                else:
                    lines.append("   Варианты: не заданы")

                if 0 <= correct < len(options):
                    lines.append(f"   Правильный ответ: {correct + 1}) {options[correct]}")
                else:
                    lines.append("   Правильный ответ: не задан")

                lines.append("   Баллы: 1")

            lines.append("")

        return "\n".join(lines)

    def save_json(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile=f"{self.test_data.get('title', 'Тест').replace(' ', '_')}.json"
        )

        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.test_data, f, ensure_ascii=False, indent=2)

            messagebox.showinfo("Успех", f"Тест сохранён:\n{path}")
            self.destroy()


# ============================================================
# Окно ученика
# ============================================================
class StudentWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("🎓 Прохождение теста")
        self.geometry("680x600")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.lift()

        self.test = None
        self.questions = []
        self.current = 0
        self.score = 0.0

        self.timer_id = None
        self.time_left = 0
        self.correct_idx = -1

        self.student = {
            "last_name": "",
            "first_name": "",
            "group": ""
        }

        self.setup_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        # Экран регистрации ученика
        self.reg_frame = tk.Frame(self, padx=30, pady=20)
        self.reg_frame.pack(fill="both", expand=True)

        tk.Label(
            self.reg_frame,
            text="Регистрация ученика",
            font=("Segoe UI", 18, "bold")
        ).pack(pady=(10, 20))

        tk.Label(
            self.reg_frame,
            text="Фамилия:",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w")

        self.ent_last = tk.Entry(self.reg_frame, font=("Segoe UI", 12))
        self.ent_last.pack(fill="x", pady=(0, 10))

        tk.Label(
            self.reg_frame,
            text="Имя:",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w")

        self.ent_first = tk.Entry(self.reg_frame, font=("Segoe UI", 12))
        self.ent_first.pack(fill="x", pady=(0, 10))

        tk.Label(
            self.reg_frame,
            text="Номер группы:",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w")

        self.ent_group = tk.Entry(self.reg_frame, font=("Segoe UI", 12))
        self.ent_group.pack(fill="x", pady=(0, 20))

        tk.Button(
            self.reg_frame,
            text="📂 Выбрать файл теста и начать",
            command=self.load_test,
            font=("Segoe UI", 13, "bold"),
            bg="#4361ee",
            fg="white",
            relief="flat"
        ).pack(pady=10, fill="x")

        tk.Label(
            self.reg_frame,
            text="После завершения теста результат будет сохранён в статистику.",
            fg="gray",
            font=("Segoe UI", 9)
        ).pack(pady=10)

        # Экран прохождения теста
        self.test_frame = tk.Frame(self, padx=20, pady=10)

        self.lbl_title = tk.Label(
            self.test_frame,
            text="",
            font=("Segoe UI", 15, "bold")
        )
        self.lbl_title.pack(pady=(10, 5))

        self.lbl_timer = tk.Label(
            self.test_frame,
            text="⏱ 00:00",
            font=("Segoe UI", 20, "bold"),
            fg="#e63946"
        )
        self.lbl_timer.pack()

        self.lbl_q = tk.Label(
            self.test_frame,
            text="",
            wraplength=560,
            font=("Segoe UI", 13),
            justify="left"
        )
        self.lbl_q.pack(pady=10)

        # Область ответов: сюда переключаем выбор ответа / письменный ответ
        self.answer_area = tk.Frame(self.test_frame)
        self.answer_area.pack(fill="x", pady=5)
        self.answer_area.columnconfigure(0, weight=1)

        # Варианты ответа
        self.opts_frame = tk.Frame(self.answer_area)
        self.opts_frame.grid(row=0, column=0, sticky="ew")

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
                activebackground="#f0f4ff"
            )
            rb.pack(pady=4, fill="x")
            self.opt_btns.append(rb)

        # Письменный ответ
        self.text_frame = tk.Frame(self.answer_area)
        self.text_frame.grid(row=0, column=0, sticky="ew")
        self.text_frame.grid_remove()

        self.lbl_text_answer = tk.Label(
            self.text_frame,
            text="Введите ответ:",
            font=("Segoe UI", 11, "bold")
        )
        self.lbl_text_answer.pack(anchor="w")

        self.answer_entry_var = tk.StringVar()
        self.ent_answer = tk.Entry(
            self.text_frame,
            textvariable=self.answer_entry_var,
            font=("Segoe UI", 13)
        )
        self.ent_answer.pack(fill="x", ipady=6)
        self.ent_answer.bind("<Return>", lambda event: self.next_q())

        self.btn_next = tk.Button(
            self.test_frame,
            text="Далее →",
            command=self.next_q,
            font=("Segoe UI", 13, "bold"),
            bg="#2a9d8f",
            fg="white",
            relief="flat",
            state="disabled"
        )
        self.btn_next.pack(pady=15)

        self.lbl_prog = tk.Label(
            self.test_frame,
            text="",
            font=("Segoe UI", 10),
            fg="gray"
        )
        self.lbl_prog.pack()

        self.lbl_points = tk.Label(
            self.test_frame,
            text="",
            font=("Segoe UI", 9),
            fg="gray"
        )
        self.lbl_points.pack()

    def load_test(self):
        last_name = self.ent_last.get().strip()
        first_name = self.ent_first.get().strip()
        group = self.ent_group.get().strip()

        if not last_name or not first_name or not group:
            messagebox.showwarning(
                "Внимание",
                "Заполните фамилию, имя и номер группы перед прохождением теста."
            )
            return

        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json")]
        )

        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                self.test = json.load(f)

            if not isinstance(self.test, dict):
                raise ValueError("Неверный формат файла теста")

            questions = copy.deepcopy(self.test.get("questions", []))

            if not isinstance(questions, list):
                raise ValueError("Неверный формат списка вопросов")

            if not questions:
                messagebox.showwarning("Внимание", "В тесте нет вопросов")
                return

            random.shuffle(questions)

            take_n = self.test.get("take_questions", len(questions))

            try:
                take_n = int(take_n)
            except ValueError:
                take_n = len(questions)

            if take_n <= 0 or take_n > len(questions):
                take_n = len(questions)

            self.questions = questions[:take_n]
            self.current = 0
            self.score = 0.0

            self.student = {
                "last_name": last_name,
                "first_name": first_name,
                "group": group
            }

            self.reg_frame.pack_forget()
            self.test_frame.pack(fill="both", expand=True)

            self.show_q()

        except Exception as e:
            messagebox.showerror(
                "Ошибка",
                f"Файл повреждён или неверный формат:\n{e}"
            )

    def show_q(self):
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None

        if self.current >= len(self.questions):
            self.finish()
            return

        q = self.questions[self.current]
        q_type = q.get("type", "choice")

        self.lbl_title.config(text=f"📝 {self.test.get('title', 'Тест')}")
        self.lbl_q.config(text=q.get("text", ""))
        self.lbl_prog.config(text=f"Вопрос {self.current + 1} из {len(self.questions)}")

        max_points = get_question_max_points(q)
        self.lbl_points.config(
            text=f"Максимум баллов за вопрос: {format_number(max_points)}"
        )

        self.btn_next.config(state="normal")

        if q_type == "text":
            self.opts_frame.grid_remove()
            self.text_frame.grid(row=0, column=0, sticky="ew")

            mode = q.get("check_mode", "exact")

            if mode == "letter":
                hint = "Введите пропущенную букву:"
            elif mode == "contains":
                hint = "Введите ответ (правильный ответ может быть в составе вашего ответа):"
            else:
                hint = "Введите ответ:"

            self.lbl_text_answer.config(text=hint)

            self.answer_entry_var.set("")
            self.ent_answer.focus_set()

            self.correct_idx = -1

        else:
            self.text_frame.grid_remove()
            self.opts_frame.grid(row=0, column=0, sticky="ew")

            self.answer_var.set("-1")

            options = q.get("options", [])
            correct = q.get("correct", 0)

            pairs = [
                (options[i], i == correct)
                for i in range(len(options))
            ]

            random.shuffle(pairs)

            self.correct_idx = next(
                (i for i, (_, is_correct) in enumerate(pairs) if is_correct),
                -1
            )

            for i, rb in enumerate(self.opt_btns):
                if i < len(pairs):
                    rb.config(text=f"{i + 1}. {pairs[i][0]}", state="normal")
                else:
                    rb.config(text="", state="disabled")

        try:
            self.time_left = int(q.get("time", 20))
        except Exception:
            self.time_left = 20

        self.update_timer()

    def update_timer(self):
        m, s = divmod(max(self.time_left, 0), 60)

        self.lbl_timer.config(text=f"⏱ {m:02d}:{s:02d}")
        self.lbl_timer.config(
            fg="#e63946" if self.time_left <= 5 else "#2b2d42"
        )

        if self.time_left > 0:
            self.timer_id = self.after(1000, self.tick)
        else:
            self.timeout()

    def tick(self):
        self.time_left -= 1
        self.update_timer()

    def timeout(self):
        self.current += 1
        self.show_q()

    def next_q(self):
        if self.current >= len(self.questions):
            self.finish()
            return

        q = self.questions[self.current]
        q_type = q.get("type", "choice")

        if q_type == "text":
            user_answer = self.answer_entry_var.get()

            if not user_answer.strip():
                messagebox.showwarning("Внимание", "Введите ответ!")
                return

            points = score_text_question(q, user_answer)
            self.score += points

        else:
            chosen = self.answer_var.get()

            if chosen == "-1":
                messagebox.showwarning("Внимание", "Выберите вариант ответа!")
                return

            if int(chosen) == self.correct_idx:
                self.score += 1.0

        self.current += 1
        self.show_q()

    def finish(self):
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None

        total = sum(get_question_max_points(q) for q in self.questions)
        grading = self.test.get("grading", {}) if self.test else {}

        def get_grade_threshold(mark):
            return safe_float(grading.get(mark, 0), 0.0)

        grade = "2"

        if self.score >= get_grade_threshold("5"):
            grade = "5"
        elif self.score >= get_grade_threshold("4"):
            grade = "4"
        elif self.score >= get_grade_threshold("3"):
            grade = "3"

        now = datetime.now()

        record = {
            "last_name": self.student.get("last_name", ""),
            "first_name": self.student.get("first_name", ""),
            "group": self.student.get("group", ""),
            "test": self.test.get("title", "Без названия") if self.test else "Без названия",
            "score": round(self.score, 2),
            "total": round(total, 2),
            "grade": grade,
            "date": now.strftime("%d.%m.%Y %H:%M"),
            "timestamp": now.timestamp()
        }

        try:
            append_statistics(record)
        except Exception as e:
            messagebox.showwarning(
                "Статистика",
                f"Не удалось сохранить статистику:\n{e}"
            )

        for w in self.winfo_children():
            w.destroy()

        tk.Label(
            self,
            text="✅ Тест завершён!",
            font=("Segoe UI", 20, "bold")
        ).pack(pady=30)

        tk.Label(
            self,
            text=f"Результат: {format_number(self.score)} из {format_number(total)}",
            font=("Segoe UI", 16)
        ).pack(pady=5)

        tk.Label(
            self,
            text=f"Оценка: {grade}",
            font=("Segoe UI", 26, "bold"),
            fg="#2a9d8f"
        ).pack(pady=15)

        tk.Label(
            self,
            text="Результат сохранён в статистику.",
            fg="gray",
            font=("Segoe UI", 10)
        ).pack(pady=5)

        tk.Button(
            self,
            text="В главное меню",
            command=self.destroy,
            font=("Segoe UI", 12),
            relief="flat"
        ).pack(pady=20)

    def on_close(self):
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None

        self.destroy()


# ============================================================
# Окно статистики
# ============================================================
class StatsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("📊 Статистика")
        self.geometry("1050x560")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        self.lift()

        self.stats = []
        self.student_map = {}

        self.setup_ui()
        self.refresh()

    def setup_ui(self):
        top = tk.Frame(self, padx=12, pady=10)
        top.pack(fill="x")

        tk.Label(
            top,
            text="Статистика прохождения тестов",
            font=("Segoe UI", 16, "bold")
        ).pack(anchor="w")

        ctrl = tk.Frame(top)
        ctrl.pack(fill="x", pady=10)

        tk.Label(
            ctrl,
            text="Ученик:",
            font=("Segoe UI", 10, "bold")
        ).pack(side="left")

        self.student_combo = ttk.Combobox(
            ctrl,
            state="readonly",
            width=55
        )
        self.student_combo.pack(side="left", padx=8)

        tk.Button(
            ctrl,
            text="🗑 Удалить статистику ученика",
            command=self.delete_student_all,
            bg="#e76f51",
            fg="white",
            relief="flat"
        ).pack(side="left", padx=5)

        tk.Button(
            ctrl,
            text="🗑 Удалить всю статистику",
            command=self.delete_all,
            bg="#d62828",
            fg="white",
            relief="flat"
        ).pack(side="left", padx=5)

        tk.Button(
            ctrl,
            text="🔄 Обновить",
            command=self.refresh
        ).pack(side="left", padx=5)

        table = tk.Frame(self, padx=12)
        table.pack(fill="both", expand=True)

        columns = ("last", "first", "group", "test", "date", "score", "grade")

        self.tree = ttk.Treeview(
            table,
            columns=columns,
            show="headings",
            selectmode="extended"
        )

        headings = [
            ("last", "Фамилия", 110),
            ("first", "Имя", 110),
            ("group", "Группа", 90),
            ("test", "Тест", 220),
            ("date", "Дата и время", 140),
            ("score", "Баллы", 100),
            ("grade", "Оценка", 70),
        ]

        for col, text, width in headings:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="w")

        vsb = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        bottom = tk.Frame(self, padx=12, pady=10)
        bottom.pack(fill="x")

        tk.Button(
            bottom,
            text="Удалить выбранную запись",
            command=self.delete_selected_record
        ).pack(side="left")

        tk.Label(
            bottom,
            text="Выберите строку в таблице, чтобы удалить одну или несколько записей.",
            fg="gray"
        ).pack(side="left", padx=10)

        tk.Button(
            bottom,
            text="Закрыть",
            command=self.destroy
        ).pack(side="right")

    def refresh(self):
        self.stats = load_statistics()

        for item in self.tree.get_children():
            self.tree.delete(item)

        indexed = list(enumerate(self.stats))

        def sort_key(item):
            timestamp = item[1].get("timestamp", 0)
            return timestamp if isinstance(timestamp, (int, float)) else 0

        indexed.sort(key=sort_key, reverse=True)

        for idx, rec in indexed:
            score = rec.get("score", "")
            total = rec.get("total", "")

            if score == "" and total == "":
                score_display = ""
            elif total == "":
                score_display = format_number(score)
            else:
                score_display = f"{format_number(score)}/{format_number(total)}"

            self.tree.insert(
                "",
                "end",
                iid=str(idx),
                values=(
                    rec.get("last_name", ""),
                    rec.get("first_name", ""),
                    rec.get("group", ""),
                    rec.get("test", ""),
                    rec.get("date", ""),
                    score_display,
                    rec.get("grade", "")
                )
            )

        self.fill_combo()

    def make_student_display(self, rec):
        return f"{rec.get('last_name', '')} {rec.get('first_name', '')} — группа {rec.get('group', '')}".strip()

    def fill_combo(self):
        current = self.student_combo.get()
        self.student_map = {}

        for rec in self.stats:
            display = self.make_student_display(rec)
            key = (
                rec.get("last_name", ""),
                rec.get("first_name", ""),
                rec.get("group", "")
            )
            self.student_map[display] = key

        values = list(self.student_map.keys())
        self.student_combo["values"] = values

        if current in self.student_map:
            self.student_combo.set(current)
        else:
            self.student_combo.set("")

    def on_tree_select(self, event=None):
        sel = self.tree.selection()

        if not sel:
            return

        try:
            idx = int(sel[0])
        except Exception:
            return

        if 0 <= idx < len(self.stats):
            display = self.make_student_display(self.stats[idx])

            if display in self.student_map:
                self.student_combo.set(display)

    def delete_selected_record(self):
        selected = self.tree.selection()

        if not selected:
            messagebox.showinfo(
                "Информация",
                "Сначала выберите запись в таблице."
            )
            return

        if not messagebox.askyesno(
            "Подтверждение",
            f"Удалить выбранные записи ({len(selected)} шт.)?"
        ):
            return

        indexes = []

        for iid in selected:
            try:
                indexes.append(int(iid))
            except Exception:
                pass

        indexes = sorted(set(indexes), reverse=True)

        for idx in indexes:
            if 0 <= idx < len(self.stats):
                self.stats.pop(idx)

        save_statistics(self.stats)
        self.refresh()

    def delete_student_all(self):
        display = self.student_combo.get().strip()
        key = self.student_map.get(display)

        if not key:
            sel = self.tree.selection()

            if sel:
                try:
                    idx = int(sel[0])
                    rec = self.stats[idx]

                    key = (
                        rec.get("last_name", ""),
                        rec.get("first_name", ""),
                        rec.get("group", "")
                    )

                    display = self.make_student_display(rec)

                except Exception:
                    pass

        if not key:
            messagebox.showinfo(
                "Информация",
                "Выберите ученика в списке или в таблице."
            )
            return

        if not messagebox.askyesno(
            "Подтверждение",
            f"Удалить всю статистику для ученика:\n{display}?"
        ):
            return

        self.stats = [
            rec for rec in self.stats
            if (
                rec.get("last_name", ""),
                rec.get("first_name", ""),
                rec.get("group", "")
            ) != key
        ]

        save_statistics(self.stats)
        self.refresh()

    def delete_all(self):
        if not self.stats:
            messagebox.showinfo("Информация", "Статистика уже пуста.")
            return

        if messagebox.askyesno(
            "Подтверждение",
            "Удалить всю статистику?\nЭто действие нельзя отменить."
        ):
            save_statistics([])
            self.refresh()


# ============================================================
# Запуск программы
# ============================================================
if __name__ == "__main__":
    app = TestApp()
    app.root.mainloop()
