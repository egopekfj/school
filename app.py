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
        self.root.geometry("1100x800")
        self.root.minsize(900, 650)
        
        self.is_fullscreen = False
        self.root.bind("<F11>", self.toggle_fullscreen)
        
        self.setup_styles()
        self.setup_context_menu()

        # Данные теста
        self.test_data = {
            "title": "Новый тест",
            "questions_to_show": 5,
            "grades": {"5": 90, "4": 75, "3": 50},
            "questions": []
        }
        
        self.editing_q_index = None
        self.current_student = {}
        self.active_questions = []
        self.current_q_index = 0
        self.student_answers = []
        self.time_left = 0
        self.timer_id = None

        self.create_main_menu()

    def setup_styles(self):
        """Шрифты и стили для высокого разрешения и полноэкранного режима"""
        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.style.configure(".", font=("Arial", 12))
        self.style.configure("MainTitle.TLabel", font=("Arial", 22, "bold"), foreground="#1e293b")
        self.style.configure("SubTitle.TLabel", font=("Arial", 16, "bold"), foreground="#334155")
        self.style.configure("Question.TLabel", font=("Arial", 17, "bold"), wraplength=850)
        self.style.configure("Timer.TLabel", font=("Arial", 15, "bold"), foreground="#dc2626")
        
        self.style.configure("Big.TButton", font=("Arial", 13, "bold"), padding=10)
        self.style.configure("Action.TButton", font=("Arial", 11), padding=6)
        self.style.configure("TRadiobutton", font=("Arial", 13), padding=4)
        
        self.style.configure("TLabelframe", padding=12)
        self.style.configure("TLabelframe.Label", font=("Arial", 13, "bold"), foreground="#2563eb")
        
        self.style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
        self.style.configure("Treeview", font=("Arial", 11), rowheight=26)

    def enable_copy_paste(self, widget):
        """Горячие клавиши копирования и вставки"""
        def select_all(event):
            widget.select_range(0, tk.END)
            return 'break'

        widget.bind("<Control-c>", lambda e: widget.event_generate("<<Copy>>"))
        widget.bind("<Control-v>", lambda e: widget.event_generate("<<Paste>>"))
        widget.bind("<Control-x>", lambda e: widget.event_generate("<<Cut>>"))
        if isinstance(widget, tk.Entry):
            widget.bind("<Control-a>", select_all)

    def setup_context_menu(self):
        """Контекстное меню мыши"""
        self.context_menu = tk.Menu(self.root, tearoff=0, font=("Arial", 11))
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
        top_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        fs_txt = "↙ Оконный режим" if self.is_fullscreen else "🔲 На весь экран (F11)"
        fs_btn = ttk.Button(top_frame, text=fs_txt, style="Action.TButton", command=self.toggle_fullscreen)
        fs_btn.pack(side=tk.RIGHT)
        return top_frame

    # --- Главное меню ---
    def create_main_menu(self):
        self.clear_screen()
        
        container = ttk.Frame(self.root, padding=25)
        container.pack(expand=True, fill=tk.BOTH)

        self.create_top_bar(container)

        center_frame = ttk.Frame(container)
        center_frame.pack(expand=True)

        ttk.Label(center_frame, text="Система тестирования", style="MainTitle.TLabel").pack(pady=(0, 25))

        ttk.Button(center_frame, text="🎓 Пройти тест (Ученик)", style="Big.TButton", width=32, command=self.start_student_mode).pack(pady=8)
        ttk.Button(center_frame, text="👨‍🏫 Конструктор тестов (Учитель)", style="Big.TButton", width=32, command=self.start_teacher_mode).pack(pady=8)
        ttk.Button(center_frame, text="📊 Статистика", style="Big.TButton", width=32, command=self.show_statistics).pack(pady=8)
        ttk.Button(center_frame, text="Выход", style="Action.TButton", width=20, command=self.root.quit).pack(pady=15)

    # --- Конструктор тестов ---
    def start_teacher_mode(self):
        self.clear_screen()
        self.editing_q_index = None
        
        container = ttk.Frame(self.root, padding=15)
        container.pack(expand=True, fill=tk.BOTH)

        self.create_top_bar(container)

        top_bar = ttk.Frame(container)
        top_bar.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(top_bar, text="⬅ Главное меню", style="Action.TButton", command=self.create_main_menu).pack(side=tk.LEFT)
        ttk.Button(top_bar, text="💾 Сохранить в JSON", style="Action.TButton", command=self.save_test_file).pack(side=tk.RIGHT, padx=5)
        ttk.Button(top_bar, text="📂 Загрузить из JSON", style="Action.TButton", command=self.load_test_file).pack(side=tk.RIGHT)

        # Настройки теста
        settings = ttk.LabelFrame(container, text="Параметры теста")
        settings.pack(fill=tk.X, pady=5)

        ttk.Label(settings, text="Название теста:", font=("Arial", 11, "bold")).grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.title_entry = ttk.Entry(settings, font=("Arial", 12), width=35)
        self.title_entry.insert(0, self.test_data.get("title", "Новый тест"))
        self.title_entry.grid(row=0, column=1, padx=5, pady=5)
        self.enable_copy_paste(self.title_entry)

        ttk.Label(settings, text="Выдавать вопросов ученику:", font=("Arial", 11, "bold")).grid(row=0, column=2, sticky=tk.W, padx=15, pady=5)
        self.q_count_entry = ttk.Entry(settings, font=("Arial", 12), width=8)
        self.q_count_entry.insert(0, str(self.test_data.get("questions_to_show", 5)))
        self.q_count_entry.grid(row=0, column=3, padx=5, pady=5)
        self.enable_copy_paste(self.q_count_entry)

        # Редактор вопроса
        q_frame = ttk.LabelFrame(container, text="Создание / Редактирование вопроса")
        q_frame.pack(fill=tk.X, pady=5)

        ttk.Label(q_frame, text="Текст вопроса:", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(0, 2))
        self.q_text = tk.Text(q_frame, height=3, font=("Arial", 12), wrap=tk.WORD)
        self.q_text.pack(fill=tk.X, pady=(0, 5))
        self.enable_copy_paste(self.q_text)

        opts_bar = ttk.Frame(q_frame)
        opts_bar.pack(fill=tk.X, pady=3)
        
        ttk.Label(opts_bar, text="Время (сек):", font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        self.q_time_entry = ttk.Entry(opts_bar, font=("Arial", 11), width=8)
        self.q_time_entry.insert(0, "60")
        self.q_time_entry.pack(side=tk.LEFT, padx=5)
        self.enable_copy_paste(self.q_time_entry)

        self.q_type_var = tk.StringVar(value="choice")
        ttk.Radiobutton(opts_bar, text="Выбор из вариантов", variable=self.q_type_var, value="choice", command=self.toggle_q_type).pack(side=tk.LEFT, padx=15)
        ttk.Radiobutton(opts_bar, text="Письменный ответ", variable=self.q_type_var, value="text", command=self.toggle_q_type).pack(side=tk.LEFT)

        self.answers_container = ttk.Frame(q_frame)
        self.answers_container.pack(fill=tk.X, pady=5)
        
        self.setup_choice_ui()

        self.add_btn = ttk.Button(q_frame, text="➕ Добавить вопрос в пул", style="Action.TButton", command=self.save_question)
        self.add_btn.pack(anchor=tk.E, pady=5)

        # Таблица Пула вопросов
        pool_frame = ttk.LabelFrame(container, text="Текущий пул вопросов теста")
        pool_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        cols = ("num", "type", "text", "time")
        self.pool_tree = ttk.Treeview(pool_frame, columns=cols, show="headings", height=5)
        self.pool_tree.heading("num", text="№")
        self.pool_tree.heading("type", text="Тип")
        self.pool_tree.heading("text", text="Текст вопроса")
        self.pool_tree.heading("time", text="Время")

        self.pool_tree.column("num", width=40, anchor=tk.CENTER)
        self.pool_tree.column("type", width=120, anchor=tk.CENTER)
        self.pool_tree.column("text", width=550)
        self.pool_tree.column("time", width=80, anchor=tk.CENTER)

        self.pool_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(pool_frame, orient=tk.VERTICAL, command=self.pool_tree.yview)
        self.pool_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        pool_btns = ttk.Frame(container)
        pool_btns.pack(fill=tk.X, pady=5)
        ttk.Button(pool_btns, text="✏️ Редактировать выбранный", style="Action.TButton", command=self.load_selected_q).pack(side=tk.LEFT, padx=5)
        ttk.Button(pool_btns, text="❌ Удалить вопрос", style="Action.TButton", command=self.delete_selected_q).pack(side=tk.LEFT)
        ttk.Button(pool_btns, text="🧹 Очистить весь пул", style="Action.TButton", command=self.clear_q_pool).pack(side=tk.RIGHT)

        self.refresh_pool_tree()

    def toggle_q_type(self):
        for w in self.answers_container.winfo_children():
            w.destroy()
        if self.q_type_var.get() == "choice":
            self.setup_choice_ui()
        else:
            self.setup_text_ui()

    def setup_choice_ui(self):
        ttk.Label(self.answers_container, text="Варианты ответов (отметьте верный точка):", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.choice_entries = []
        self.correct_choice_var = tk.IntVar(value=0)

        for i in range(4):
            f = ttk.Frame(self.answers_container)
            f.pack(fill=tk.X, pady=2)
            rb = ttk.Radiobutton(f, variable=self.correct_choice_var, value=i)
            rb.pack(side=tk.LEFT)
            e = ttk.Entry(f, font=("Arial", 11))
            e.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            self.enable_copy_paste(e)
            self.choice_entries.append(e)

    def setup_text_ui(self):
        ttk.Label(self.answers_container, text="Правильный ответ (варианты разделите знаками ;):", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.text_ans_entry = ttk.Entry(self.answers_container, font=("Arial", 12))
        self.text_ans_entry.pack(fill=tk.X, pady=3)
        self.enable_copy_paste(self.text_ans_entry)

        self.match_rule_var = tk.StringVar(value="exact")
        f = ttk.Frame(self.answers_container)
        f.pack(fill=tk.X, pady=2)
        ttk.Radiobutton(f, text="Точное совпадение", variable=self.match_rule_var, value="exact").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(f, text="Гибкая проверка (учет знаков и букв)", variable=self.match_rule_var, value="char_match").pack(side=tk.LEFT, padx=15)

    def refresh_pool_tree(self):
        for item in self.pool_tree.get_children():
            self.pool_tree.delete(item)
        
        for idx, q in enumerate(self.test_data.get("questions", [])):
            q_type_str = "Выбор" if q["type"] == "choice" else "Письменный"
            self.pool_tree.insert("", tk.END, values=(idx + 1, q_type_str, q["text"], f"{q.get('time', 60)}с"))

    def save_question(self):
        text = self.q_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Ошибка", "Введите текст вопроса")
            return

        time_val = int(self.q_time_entry.get() or 60)
        q_type = self.q_type_var.get()

        if q_type == "choice":
            opts = [e.get().strip() for e in self.choice_entries if e.get().strip()]
            if len(opts) < 2:
                messagebox.showwarning("Ошибка", "Заполните минимум 2 варианта ответа")
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
                messagebox.showwarning("Ошибка", "Укажите правильный ответ")
                return
            q_data = {
                "type": "text",
                "text": text,
                "time": time_val,
                "correct": ans,
                "rule": self.match_rule_var.get()
            }

        if self.editing_q_index is not None:
            self.test_data["questions"][self.editing_q_index] = q_data
            self.editing_q_index = None
            self.add_btn.config(text="➕ Добавить вопрос в пул")
            messagebox.showinfo("Успех", "Вопрос обновлен!")
        else:
            self.test_data["questions"].append(q_data)
            messagebox.showinfo("Успех", "Вопрос добавлен в пул!")

        self.q_text.delete("1.0", tk.END)
        self.refresh_pool_tree()

    def load_selected_q(self):
        selected = self.pool_tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите вопрос из таблицы")
            return
        
        idx = int(self.pool_tree.item(selected[0])['values'][0]) - 1
        q = self.test_data["questions"][idx]
        self.editing_q_index = idx

        self.q_text.delete("1.0", tk.END)
        self.q_text.insert("1.0", q["text"])
        self.q_time_entry.delete(0, tk.END)
        self.q_time_entry.insert(0, str(q.get("time", 60)))
        
        self.q_type_var.set(q["type"])
        self.toggle_q_type()

        if q["type"] == "choice":
            for i, opt in enumerate(q.get("options", [])):
                if i < len(self.choice_entries):
                    self.choice_entries[i].insert(0, opt)
            self.correct_choice_var.set(q.get("correct", 0))
        else:
            self.text_ans_entry.insert(0, q.get("correct", ""))
            self.match_rule_var.set(q.get("rule", "exact"))

        self.add_btn.config(text="💾 Сохранить изменения вопроса")

    def delete_selected_q(self):
        selected = self.pool_tree.selection()
        if not selected:
            messagebox.showwarning("Ошибка", "Выберите вопрос для удаления")
            return
        idx = int(self.pool_tree.item(selected[0])['values'][0]) - 1
        del self.test_data["questions"][idx]
        self.refresh_pool_tree()

    def clear_q_pool(self):
        if messagebox.askyesno("Подтверждение", "Очистить весь пул вопросов?"):
            self.test_data["questions"] = []
            self.refresh_pool_tree()

    def save_test_file(self):
        self.test_data["title"] = self.title_entry.get().strip()
        self.test_data["questions_to_show"] = int(self.q_count_entry.get() or 5)
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON файлы", "*.json")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.test_data, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Сохранено", "Файл теста с пулом вопросов сохранен!")

    def load_test_file(self):
        path = filedialog.askopenfilename(filetypes=[("JSON файлы", "*.json")])
        if path:
            with open(path, "r", encoding="utf-8") as f:
                self.test_data = json.load(f)
            self.start_teacher_mode()

    # --- Режим ученика ---
    def start_student_mode(self):
        self.clear_screen()
        container = ttk.Frame(self.root, padding=25)
        container.pack(expand=True, fill=tk.BOTH)

        self.create_top_bar(container)

        center = ttk.Frame(container)
        center.pack(expand=True)

        ttk.Label(center, text="Авторизация ученика", style="SubTitle.TLabel").pack(pady=(0, 20))

        form = ttk.Frame(center)
        form.pack(pady=10)

        ttk.Label(form, text="Фамилия и Имя:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky=tk.W, pady=8)
        name_entry = ttk.Entry(form, font=("Arial", 13), width=28)
        name_entry.grid(row=0, column=1, pady=8, padx=10)
        self.enable_copy_paste(name_entry)

        ttk.Label(form, text="Класс / Группа:", font=("Arial", 12, "bold")).grid(row=1, column=0, sticky=tk.W, pady=8)
        group_entry = ttk.Entry(form, font=("Arial", 13), width=28)
        group_entry.grid(row=1, column=1, pady=8, padx=10)
        self.enable_copy_paste(group_entry)

        def proceed():
            name = name_entry.get().strip()
            group = group_entry.get().strip()
            if not name or not group:
                messagebox.showwarning("Ошибка", "Заполните все поля")
                return
            
            path = filedialog.askopenfilename(title="Выберите файл теста (.json)", filetypes=[("JSON файлы", "*.json")])
            if not path:
                return
            
            with open(path, "r", encoding="utf-8") as f:
                self.test_data = json.load(f)

            if not self.test_data.get("questions"):
                messagebox.showerror("Ошибка", "В этом файле теста нет вопросов!")
                return

            self.current_student = {"name": name, "group": group}
            self.prepare_test()

        ttk.Button(center, text="📂 Выбрать файл теста и начать", style="Big.TButton", command=proceed).pack(pady=20)
        ttk.Button(center, text="⬅ Назад", style="Action.TButton", command=self.create_main_menu).pack()

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

        container = ttk.Frame(self.root, padding=20)
        container.pack(expand=True, fill=tk.BOTH)

        self.create_top_bar(container)

        header = ttk.Frame(container)
        header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header, text=f"Вопрос {self.current_q_index + 1} из {len(self.active_questions)}", font=("Arial", 13, "bold")).pack(side=tk.LEFT)
        self.timer_label = ttk.Label(header, text=f"⏱ Время: {self.time_left} с", style="Timer.TLabel")
        self.timer_label.pack(side=tk.RIGHT)

        q_card = ttk.LabelFrame(container, text=f"Тест: {self.test_data.get('title', 'Без названия')}")
        q_card.pack(fill=tk.BOTH, expand=True, pady=10)

        ttk.Label(q_card, text=q["text"], style="Question.TLabel").pack(anchor=tk.W, pady=15, padx=10)

        self.ans_var = tk.StringVar()
        ans_area = ttk.Frame(q_card)
        ans_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        if q["type"] == "choice":
            for i, opt in enumerate(q["options"]):
                ttk.Radiobutton(ans_area, text=opt, variable=self.ans_var, value=str(i)).pack(anchor=tk.W, pady=6)
        else:
            ttk.Label(ans_area, text="Введите ваш ответ (знак '-' или текст):", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 5))
            entry = ttk.Entry(ans_area, textvariable=self.ans_var, font=("Arial", 15), width=40)
            entry.pack(anchor=tk.W, pady=10)
            entry.focus()
            self.enable_copy_paste(entry)

        ttk.Button(container, text="Следующий вопрос ➔", style="Big.TButton", command=self.next_question).pack(anchor=tk.E, pady=10)

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

    # --- Алгоритм проверки ---
    def calculate_score(self):
        total_score = 0.0
        max_score = len(self.active_questions)

        for i, q in enumerate(self.active_questions):
            ans = self.student_answers[i]
            if not ans:
                continue

            if q["type"] == "choice":
                if str(q["correct"]) == ans:
                    total_score += 1.0
            else:
                correct_variants = [v.strip().lower() for v in q["correct"].split(";")]
                user_ans_clean = ans.lower().strip()

                if q.get("rule") == "exact":
                    if user_ans_clean in correct_variants:
                        total_score += 1.0
                else:
                    best_match = 0.0
                    for var in correct_variants:
                        if user_ans_clean == var:
                            best_match = 1.0
                            break
                        matches = sum(1 for c in user_ans_clean if c in var or c == '-')
                        score = matches / max(len(var), 1)
                        if score > best_match:
                            best_match = score

                    total_score += min(best_match, 1.0)

        percent = (total_score / max_score * 100) if max_score > 0 else 0.0
        
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

        container = ttk.Frame(self.root, padding=25)
        container.pack(expand=True, fill=tk.BOTH)

        self.create_top_bar(container)

        center = ttk.Frame(container)
        center.pack(expand=True)

        ttk.Label(center, text="Результаты тестирования", style="MainTitle.TLabel").pack(pady=(0, 15))
        
        info_card = ttk.LabelFrame(center, text="Детали прохождения", padding=15)
        info_card.pack(fill=tk.X, pady=10)

        ttk.Label(info_card, text=f"Тест: {test_title}", font=("Arial", 13, "bold")).pack(anchor=tk.W, pady=2)
        ttk.Label(info_card, text=f"Ученик: {self.current_student['name']} ({self.current_student['group']})", font=("Arial", 12)).pack(anchor=tk.W, pady=2)
        ttk.Label(info_card, text=f"Набранный балл: {score} из {max_s} ({percent}%)", font=("Arial", 13, "bold")).pack(anchor=tk.W, pady=5)

        color = "#16a34a" if grade >= 4 else ("#d97706" if grade == 3 else "#dc2626")
        ttk.Label(center, text=f"Итоговая оценка: {grade}", font=("Arial", 30, "bold"), foreground=color).pack(pady=15)

        ttk.Button(center, text="В главное меню", style="Big.TButton", command=self.create_main_menu).pack(pady=10)

    # --- Статистика ---
    def show_statistics(self):
        self.clear_screen()
        container = ttk.Frame(self.root, padding=15)
        container.pack(expand=True, fill=tk.BOTH)

        self.create_top_bar(container)

        top = ttk.Frame(container)
        top.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(top, text="⬅ Главное меню", style="Action.TButton", command=self.create_main_menu).pack(side=tk.LEFT)
        ttk.Button(top, text="🗑 Очистить историю", style="Action.TButton", command=self.clear_statistics).pack(side=tk.RIGHT)

        ttk.Label(container, text="Результаты тестирования учеников", style="SubTitle.TLabel").pack(pady=5)

        cols = ("date", "test_title", "name", "group", "score", "percent", "grade")
        tree = ttk.Treeview(container, columns=cols, show="headings")
        
        tree.heading("date", text="Дата")
        tree.heading("test_title", text="Название теста")
        tree.heading("name", text="ФИО ученика")
        tree.heading("group", text="Класс")
        tree.heading("score", text="Баллы")
        tree.heading("percent", text="Процент")
        tree.heading("grade", text="Оценка")

        tree.column("date", width=130, anchor=tk.CENTER)
        tree.column("test_title", width=220)
        tree.column("name", width=200)
        tree.column("group", width=80, anchor=tk.CENTER)
        tree.column("score", width=80, anchor=tk.CENTER)
        tree.column("percent", width=80, anchor=tk.CENTER)
        tree.column("grade", width=70, anchor=tk.CENTER)

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
        if messagebox.askyesno("Подтверждение", "Удалить всю статистику?"):
            if os.path.exists("test_statistics.json"):
                os.remove("test_statistics.json")
            self.show_statistics()

if __name__ == "__main__":
    root = tk.Tk()
    app = TestApp(root)
    root.mainloop()
