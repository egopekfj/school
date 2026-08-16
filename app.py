import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import random
import copy
import os
from datetime import datetime

class TestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Система тестирования")
        self.root.geometry("900x650")
        
        # Настройка полноэкранного режима
        self.is_fullscreen = False
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.setup_context_menu()

        # Данные теста
        self.test_data = {
            "title": "Новый тест",
            "questions_to_show": 5,
            "grades": {"5": 90, "4": 75, "3": 50},
            "questions": []
        }
        
        # Переменные прохождения
        self.current_student = {}
        self.active_questions = []
        self.current_q_index = 0
        self.student_answers = []
        self.time_left = 0
        self.timer_id = None

        self.create_main_menu()

    def enable_copy_paste(self, widget):
        """Включает горячие клавиши CTRL+C, CTRL+V, CTRL+A, CTRL+X"""
        def select_all(event):
            widget.select_range(0, tk.END)
            return 'break'

        widget.bind("<Control-c>", lambda e: widget.event_generate("<<Copy>>"))
        widget.bind("<Control-v>", lambda e: widget.event_generate("<<Paste>>"))
        widget.bind("<Control-x>", lambda e: widget.event_generate("<<Cut>>"))
        if isinstance(widget, tk.Entry):
            widget.bind("<Control-a>", select_all)

    def setup_context_menu(self):
        """Контекстное меню мыши для вставки/копирования"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Копировать", command=lambda: self.root.focus_get().event_generate("<<Copy>>"))
        self.context_menu.add_command(label="Вставить", command=lambda: self.root.focus_get().event_generate("<<Paste>>"))
        self.context_menu.add_command(label="Вырезать", command=lambda: self.root.focus_get().event_generate("<<Cut>>"))

        self.root.bind_class("Entry", "<Button-3>", self.show_context_menu)
        self.root.bind_class("Text", "<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes("-fullscreen", self.is_fullscreen)

    def clear_screen(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        for widget in self.root.winfo_children():
            widget.destroy()

    def create_top_bar(self, parent):
        top_frame = ttk.Frame(parent)
        top_frame.pack(fill=tk.X, pady=5, px=10)
        fs_btn = ttk.Button(top_frame, text="🔲 На весь экран (F11)", command=self.toggle_fullscreen)
        fs_btn.pack(side=tk.RIGHT)
        return top_frame

    # --- Главное меню ---
    def create_main_menu(self):
        self.clear_screen()
        
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(expand=True, fill=tk.BOTH)

        self.create_top_bar(main_frame)

        ttk.Label(main_frame, text="Система тестирования", font=("Arial", 22, "bold")).pack(pady=20)

        btn_style = {'width': 35, 'padding': 10}
        
        ttk.Button(main_frame, text="🎓 Пройти тест (Ученик)", command=self.start_student_mode, **btn_style).pack(pady=10)
        ttk.Button(main_frame, text="👨‍🏫 Конструктор тестов (Учитель)", command=self.start_teacher_mode, **btn_style).pack(pady=10)
        ttk.Button(main_frame, text="📊 Статистика", command=self.show_statistics, **btn_style).pack(pady=10)
        ttk.Button(main_frame, text="Выход", command=self.root.quit, **btn_style).pack(pady=10)

    # --- Конструктор тестов ---
    def start_teacher_mode(self):
        self.clear_screen()
        
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(expand=True, fill=tk.BOTH)

        self.create_top_bar(main_frame)

        # Шапка
        top_bar = ttk.Frame(main_frame)
        top_bar.pack(fill=tk.X, pady=5)
        ttk.Button(top_bar, text="⬅ Главное меню", command=self.create_main_menu).pack(side=tk.LEFT)
        ttk.Button(top_bar, text="💾 Сохранить тест в JSON", command=self.save_test_file).pack(side=tk.RIGHT, padx=5)
        ttk.Button(top_bar, text="📂 Загрузить тест из JSON", command=self.load_test_file).pack(side=tk.RIGHT)

        # Настройки теста
        settings_frame = ttk.LabelFrame(main_frame, text="Настройки теста", padding=10)
        settings_frame.pack(fill=tk.X, pady=5)

        ttk.Label(settings_frame, text="Название:").grid(row=0, column=0, sticky=tk.W)
        self.title_entry = ttk.Entry(settings_frame, width=40)
        self.title_entry.insert(0, self.test_data.get("title", "Новый тест"))
        self.title_entry.grid(row=0, column=1, padx=5)
        self.enable_copy_paste(self.title_entry)

        ttk.Label(settings_frame, text="Вопросов ученику:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.q_count_entry = ttk.Entry(settings_frame, width=5)
        self.q_count_entry.insert(0, str(self.test_data.get("questions_to_show", 5)))
        self.q_count_entry.grid(row=0, column=3)
        self.enable_copy_paste(self.q_count_entry)

        # Форма добавления вопроса
        q_frame = ttk.LabelFrame(main_frame, text="Добавить / Редактировать вопрос", padding=10)
        q_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        ttk.Label(q_frame, text="Текст вопроса:").pack(anchor=tk.W)
        self.q_text = tk.Text(q_frame, height=3, width=70)
        self.q_text.pack(fill=tk.X, pady=2)
        self.enable_copy_paste(self.q_text)

        ttk.Label(q_frame, text="Время на вопрос (сек):").pack(anchor=tk.W)
        self.q_time_entry = ttk.Entry(q_frame, width=10)
        self.q_time_entry.insert(0, "60")
        self.q_time_entry.pack(anchor=tk.W, pady=2)
        self.enable_copy_paste(self.q_time_entry)

        # Тип вопроса
        self.q_type_var = tk.StringVar(value="choice")
        type_frame = ttk.Frame(q_frame)
        type_frame.pack(fill=tk.X, pady=5)
        ttk.Radiobutton(type_frame, text="Выбор ответа", variable=self.q_type_var, value="choice", command=self.toggle_q_type).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="Письменный ответ", variable=self.q_type_var, value="text", command=self.toggle_q_type).pack(side=tk.LEFT, padx=5)

        # Контейнер для вариантов или текста
        self.answers_container = ttk.Frame(q_frame)
        self.answers_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.setup_choice_ui()

        ttk.Button(q_frame, text="➕ Добавить вопрос в тест", command=self.add_question).pack(pady=5)

    def toggle_q_type(self):
        for w in self.answers_container.winfo_children():
            w.destroy()
        if self.q_type_var.get() == "choice":
            self.setup_choice_ui()
        else:
            self.setup_text_ui()

    def setup_choice_ui(self):
        ttk.Label(self.answers_container, text="Варианты ответов (отметьте верный):").pack(anchor=tk.W)
        self.choice_entries = []
        self.correct_choice_var = tk.IntVar(value=0)

        for i in range(4):
            f = ttk.Frame(self.answers_container)
            f.pack(fill=tk.X, pady=2)
            rb = ttk.Radiobutton(f, variable=self.correct_choice_var, value=i)
            rb.pack(side=tk.LEFT)
            e = ttk.Entry(f)
            e.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            self.enable_copy_paste(e)
            self.choice_entries.append(e)

    def setup_text_ui(self):
        ttk.Label(self.answers_container, text="Правильный ответ (если несколько, разделите знаками ;):").pack(anchor=tk.W)
        self.text_ans_entry = ttk.Entry(self.answers_container)
        self.text_ans_entry.pack(fill=tk.X, pady=2)
        self.enable_copy_paste(self.text_ans_entry)

        ttk.Label(self.answers_container, text="Правило проверки символов/букв:").pack(anchor=tk.W, pady=(5,0))
        self.match_rule_var = tk.StringVar(value="exact")
        rules = [
            ("Точное совпадение слова/фразы", "exact"),
            ("Проверка букв, слов и знаков (включая '-')", "char_match")
        ]
        for text, val in rules:
            ttk.Radiobutton(self.answers_container, text=text, variable=self.match_rule_var, value=val).pack(anchor=tk.W)

    def add_question(self):
        text = self.q_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Ошибка", "Введите текст вопроса")
            return

        time_val = int(self.q_time_entry.get() or 60)
        q_type = self.q_type_var.get()

        if q_type == "choice":
            opts = [e.get().strip() for e in self.choice_entries if e.get().strip()]
            if len(opts) < 2:
                messagebox.showwarning("Ошибка", "Заполните хотя бы 2 варианта ответа")
                return
            q_data = {
                "type": "choice",
                "text": text,
                "time": time_val,
                "options": opts,
                "correct": self.correct_choice_var.get()
            }
        else:
            ans = self.text_ans_entry.get().strip()
            if not ans:
                messagebox.showwarning("Ошибка", "Укажите верный ответ")
                return
            q_data = {
                "type": "text",
                "text": text,
                "time": time_val,
                "correct": ans,
                "rule": self.match_rule_var.get()
            }

        self.test_data["questions"].append(q_data)
        messagebox.showinfo("Успех", "Вопрос успешно добавлен!")
        self.q_text.delete("1.0", tk.END)

    def save_test_file(self):
        self.test_data["title"] = self.title_entry.get().strip()
        self.test_data["questions_to_show"] = int(self.q_count_entry.get() or 5)
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.test_data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Сохранено", "Тест успешно сохранён!")

    def load_test_file(self):
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if path:
            with open(path, "r", encoding="utf-8") as f:
                self.test_data = json.load(f)
            self.start_teacher_mode()

    # --- Режим ученика ---
    def start_student_mode(self):
        self.clear_screen()
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(expand=True, fill=tk.BOTH)

        self.create_top_bar(main_frame)

        ttk.Label(main_frame, text="Регистрация ученика", font=("Arial", 16, "bold")).pack(pady=10)

        form = ttk.Frame(main_frame)
        form.pack(pady=10)

        ttk.Label(form, text="Фамилия и Имя:").grid(row=0, column=0, sticky=tk.W, pady=5)
        name_entry = ttk.Entry(form, width=30)
        name_entry.grid(row=0, column=1, pady=5)
        self.enable_copy_paste(name_entry)

        ttk.Label(form, text="Класс / Группа:").grid(row=1, column=0, sticky=tk.W, pady=5)
        group_entry = ttk.Entry(form, width=30)
        group_entry.grid(row=1, column=1, pady=5)
        self.enable_copy_paste(group_entry)

        def proceed():
            name = name_entry.get().strip()
            group = group_entry.get().strip()
            if not name or not group:
                messagebox.showwarning("Ошибка", "Заполните все поля")
                return
            
            path = filedialog.askopenfilename(title="Выберите файл теста", filetypes=[("JSON files", "*.json")])
            if not path:
                return
            
            with open(path, "r", encoding="utf-8") as f:
                self.test_data = json.load(f)

            self.current_student = {"name": name, "group": group}
            self.prepare_test()

        ttk.Button(main_frame, text="📂 Выбрать файл теста и начать", command=proceed).pack(pady=20)
        ttk.Button(main_frame, text="⬅ Назад", command=self.create_main_menu).pack()

    def prepare_test(self):
        qs = copy.deepcopy(self.test_data.get("questions", []))
        random.shuffle(qs)
        limit = min(self.test_data.get("questions_to_show", len(qs)), len(qs))
        self.active_questions = qs[:limit]
        self.current_q_index = 0
        self.student_answers = []
        self.run_question()

    def run_question(self):
        self.clear_screen()
        if self.current_q_index >= len(self.active_questions):
            self.finish_test()
            return

        q = self.active_questions[self.current_q_index]
        self.time_left = q.get("time", 60)

        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(expand=True, fill=tk.BOTH)

        self.create_top_bar(main_frame)

        # Шапка с таймером
        header = ttk.Frame(main_frame)
        header.pack(fill=tk.X)
        ttk.Label(header, text=f"Вопрос {self.current_q_index + 1} из {len(self.active_questions)}", font=("Arial", 12)).pack(side=tk.LEFT)
        self.timer_label = ttk.Label(header, text=f"⏱ Время: {self.time_left} с", font=("Arial", 12, "bold"), foreground="red")
        self.timer_label.pack(side=tk.RIGHT)

        ttk.Label(main_frame, text=q["text"], font=("Arial", 14), wraplength=700).pack(pady=20)

        self.ans_var = tk.StringVar()

        if q["type"] == "choice":
            for i, opt in enumerate(q["options"]):
                ttk.Radiobutton(main_frame, text=opt, variable=self.ans_var, value=str(i)).pack(anchor=tk.W, pady=5)
        else:
            ttk.Label(main_frame, text="Введите ваш ответ (символы/буквы/слово, включая '-'):").pack(anchor=tk.W)
            entry = ttk.Entry(main_frame, textvariable=self.ans_var, width=40, font=("Arial", 12))
            entry.pack(pady=10, anchor=tk.W)
            entry.focus()
            self.enable_copy_paste(entry)

        ttk.Button(main_frame, text="Ответить ➔", command=self.next_question).pack(pady=20)

        self.update_timer()

    def update_timer(self):
        if self.time_left > 0:
            self.timer_label.config(text=f"⏱ Время: {self.time_left} с")
            self.time_left -= 1
            self.timer_id = self.root.after(1000, self.update_timer)
        else:
            self.next_question()

    def next_question(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

        user_ans = self.ans_var.get().strip() if hasattr(self, 'ans_var') else ""
        self.student_answers.append(user_ans)
        self.current_q_index += 1
        self.run_question()

    def calculate_score(self):
        total_score = 0
        max_score = len(self.active_questions)

        for i, q in enumerate(self.active_questions):
            ans = self.student_answers[i]
            if not ans:
                continue

            if q["type"] == "choice":
                if str(q["correct"]) == ans:
                    total_score += 1
            else:
                correct_variants = [v.strip().lower() for v in q["correct"].split(";")]
                user_ans_clean = ans.lower()

                if q.get("rule") == "exact":
                    if user_ans_clean in correct_variants:
                        total_score += 1
                else:
                    # Учитывает символы, буквы, дефисы и пропуски "-"
                    best_match = 0
                    for var in correct_variants:
                        matches = sum(1 for c in user_ans_clean if c in var or c == '-')
                        score = matches / max(len(var), 1)
                        if score > best_match:
                            best_match = score
                    total_score += min(best_match, 1.0)

        percent = (total_score / max_score * 100) if max_score > 0 else 0
        
        grades = self.test_data.get("grades", {"5": 90, "4": 75, "3": 50})
        if percent >= grades.get("5", 90):
            grade = 5
        elif percent >= grades.get("4", 75):
            grade = 4
        elif percent >= grades.get("3", 50):
            grade = 3
        else:
            grade = 2

        return round(total_score, 1), max_score, round(percent, 1), grade

    def finish_test(self):
        self.clear_screen()
        score, max_s, percent, grade = self.calculate_score()

        # Сохранение статистики с именем теста
        test_title = self.test_data.get("title", "Тест без названия")
        stat_entry = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "test_title": test_title,
            "name": self.current_student["name"],
            "group": self.current_student["group"],
            "score": f"{score}/{max_s}",
            "percent": f"{percent}%",
            "grade": grade
        }

        stats = []
        if os.path.exists("test_statistics.json"):
            try:
                with open("test_statistics.json", "r", encoding="utf-8") as f:
                    stats = json.load(f)
            except:
                stats = []

        stats.append(stat_entry)
        with open("test_statistics.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=4)

        # Вывод результатов
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(expand=True, fill=tk.BOTH)

        self.create_top_bar(main_frame)

        ttk.Label(main_frame, text="Тест завершён!", font=("Arial", 18, "bold")).pack(pady=10)
        ttk.Label(main_frame, text=f"Тест: {test_title}", font=("Arial", 12)).pack(pady=2)
        ttk.Label(main_frame, text=f"Ученик: {self.current_student['name']} ({self.current_student['group']})").pack(pady=2)
        ttk.Label(main_frame, text=f"Результат: {score} из {max_s} ({percent}%)", font=("Arial", 14)).pack(pady=10)
        
        color = "green" if grade >= 4 else ("orange" if grade == 3 else "red")
        ttk.Label(main_frame, text=f"Оценка: {grade}", font=("Arial", 26, "bold"), foreground=color).pack(pady=10)

        ttk.Button(main_frame, text="В главное меню", command=self.create_main_menu).pack(pady=20)

    # --- Статистика ---
    def show_statistics(self):
        self.clear_screen()
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(expand=True, fill=tk.BOTH)

        self.create_top_bar(main_frame)

        top = ttk.Frame(main_frame)
        top.pack(fill=tk.X, pady=5)
        ttk.Button(top, text="⬅ Главное меню", command=self.create_main_menu).pack(side=tk.LEFT)
        ttk.Button(top, text="🗑 Очистить историю", command=self.clear_statistics).pack(side=tk.RIGHT)

        ttk.Label(main_frame, text="Результаты тестирования", font=("Arial", 16, "bold")).pack(pady=10)

        # Добавлена колонка Название теста (test_title)
        cols = ("date", "test_title", "name", "group", "score", "percent", "grade")
        tree = ttk.Treeview(main_frame, columns=cols, show="headings")
        
        tree.heading("date", text="Дата")
        tree.heading("test_title", text="Название теста")
        tree.heading("name", text="ФИО ученика")
        tree.heading("group", text="Класс/Группа")
        tree.heading("score", text="Баллы")
        tree.heading("percent", text="Процент")
        tree.heading("grade", text="Оценка")

        tree.column("date", width=120)
        tree.column("test_title", width=180)
        tree.column("name", width=160)
        tree.column("group", width=90)
        tree.column("score", width=70)
        tree.column("percent", width=70)
        tree.column("grade", width=60)

        tree.pack(fill=tk.BOTH, expand=True)

        if os.path.exists("test_statistics.json"):
            try:
                with open("test_statistics.json", "r", encoding="utf-8") as f:
                    stats = json.load(f)
                    for item in reversed(stats):
                        tree.insert("", tk.END, values=(
                            item.get("date", "-"),
                            item.get("test_title", "Тест"),
                            item.get("name", "-"),
                            item.get("group", "-"),
                            item.get("score", "-"),
                            item.get("percent", "-"),
                            item.get("grade", "-")
                        ))
            except:
                pass

    def clear_statistics(self):
        if messagebox.askyesno("Подтверждение", "Удалить все данные статистики?"):
            if os.path.exists("test_statistics.json"):
                os.remove("test_statistics.json")
            self.show_statistics()

if __name__ == "__main__":
    root = tk.Tk()
    app = TestApp(root)
    root.mainloop()
