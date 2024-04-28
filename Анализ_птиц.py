import tkinter as tk
from tkinter import ttk, filedialog
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import messagebox
import folium
import tempfile
import webview
import scipy.stats as stats
import seaborn as sns
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

#Основные настройки
current_version = 'v1.7'
root = tk.Tk()
root.title("Анализ птиц")
root.state('zoomed')


# Загрузка данных
file_path = '_internal/botiev2017.xlsx'
data = pd.read_excel(file_path)

global database_label
year = file_path.split('botiev')[1][:4]


def initialize_table():
    update_table(data)


# Преобразование дат
data['Дата-время наблюдения'] = pd.to_datetime(data['Дата-время наблюдения'], errors='coerce')


# Определение сезона по месяцу
def load_file():
    file_path = filedialog.askopenfilename(title="Выберите файл Excel",
                                           filetypes=[("Excel files", "*.xlsx *.xls")])
    if file_path:
        global data
        global year
        global database_label
        data = pd.read_excel(file_path)
        data['Дата-время наблюдения'] = pd.to_datetime(data['Дата-время наблюдения'], errors='coerce')
        data['Сезон'] = data['Дата-время наблюдения'].apply(get_season)
        update_table(data)
        bird_options = ["Все виды"] + sorted(data['Вид птицы'].unique().tolist())
        bird_menu['menu'].delete(0, 'end')
        for option in bird_options:
            bird_menu['menu'].add_command(label=option, command=tk._setit(bird_var, option))
        bird_var.set(bird_options[0])
        season_var.set(season_options[0])

        # Извлекаем год из имени файла и обновляем надпись
        year = file_path.split('/')[-1].split('botiev')[1][
               :4]  # Исправьте разделитель на '\\' если используется Windows
        database_label.config(text=f'База данных птиц за {year} г.')


toolbar = ttk.Frame(root)
toolbar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
load_button = ttk.Button(toolbar, text="Загрузить файл", command=load_file)
load_button.pack(side=tk.LEFT)


def show_map():
    # Пересоздаем карту с учетом текущих данных в таблице
    global m
    filtered_data = []
    for item in tree.get_children():
        row = tree.item(item, "values")
        filtered_data.append(row)

    if filtered_data:
        # Преобразуем список списков в DataFrame
        filtered_df = pd.DataFrame(filtered_data, columns=data.columns)

        # Преобразуем строки в нужные типы данных, если это необходимо
        filtered_df['Координаты старта (Lat Long)'] = filtered_df['Координаты старта (Lat Long)'].apply(lambda x: tuple(map(float, x.split(' '))))
        filtered_df['Координаты финиша (Lat Long)'] = filtered_df['Координаты финиша (Lat Long)'].apply(lambda x: tuple(map(float, x.split(' '))))

        # Создаем карту
        if not filtered_df.empty:
            start_coords = filtered_df['Координаты старта (Lat Long)'].iloc[0]
            m = folium.Map(location=start_coords, zoom_start=12)

            # Добавляем метки для старта и финиша
            for index, row in filtered_df.iterrows():
                folium.Marker(row['Координаты старта (Lat Long)'], icon=folium.Icon(color='green'), tooltip="Старт").add_to(m)
                folium.Marker(row['Координаты финиша (Lat Long)'], icon=folium.Icon(color='red'), tooltip="Финиш").add_to(m)
                folium.PolyLine([row['Координаты старта (Lat Long)'], row['Координаты финиша (Lat Long)']], color='blue').add_to(m)

            # Сохраняем карту в HTML и отображаем
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
            m.save(temp_file.name)
            temp_file.close()
            webview.create_window('Карта маршрута', temp_file.name)
            webview.start()
        else:
            messagebox.showinfo("Информация", "Нет данных для отображения на карте.")

        # Сохраняем карту в HTML
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
        m.save(temp_file.name)
        temp_file.close()

        # Отображение карты в HTMLLabel внутри приложения Tkinter
        webview.create_window('Карта маршрута', temp_file.name)
        webview.start()


# Добавление кнопки для показа карты
map_button = ttk.Button(toolbar, text="Показать карту", command=show_map)
map_button.pack(side=tk.LEFT)
database_label = ttk.Label(toolbar, text=f'База данных птиц за {year} г.')
database_label.pack(side=tk.RIGHT)


def get_season(date):
    month = date.month
    if 3 <= month <= 5:
        return 'Весна'
    elif 6 <= month <= 8:
        return 'Лето'
    elif 9 <= month <= 11:
        return 'Осень'
    else:
        return 'Зима'


data['Сезон'] = data['Дата-время наблюдения'].apply(get_season)


# Функция для обновления таблицы
def update_table(filtered_data):
    for row in tree.get_children():
        tree.delete(row)
    for _, row in filtered_data.iterrows():
        tree.insert("", "end", values=list(row))


# Функция фильтрации данных
def filter_data():
    bird_type = bird_var.get()
    season = season_var.get()
    filtered_data = data
    if bird_type != "Все виды":
        filtered_data = filtered_data[filtered_data['Вид птицы'] == bird_type]
    if season != "Весь период":
        filtered_data = filtered_data[filtered_data['Сезон'] == season]
    update_table(filtered_data)
    update_status(filtered_data)


# Функция для отображения гистограммы
def show_histogram():
    bird_type = bird_var.get()
    season = season_var.get()
    filtered_data = data
    if bird_type != "Все виды":
        filtered_data = filtered_data[filtered_data['Вид птицы'] == bird_type]
    if season != "Весь период":
        filtered_data = filtered_data[filtered_data['Сезон'] == season]

    # Создаем гистограмму
    counts, bins, patches = plt.hist(filtered_data['Высота миграции, метров'],
                                     weights=filtered_data['Кол-во птиц в миграции'],
                                     bins=20, color='blue', alpha=0.7)

    for rect in patches:
        height = rect.get_height()
        if(height > 0):
            plt.text(rect.get_x() + rect.get_width() / 2., height, f'{int(height)}',
                     ha='center', va='bottom')

    plt.title(f'Распределение высоты полета для {bird_type}, {season}')
    plt.xlabel('Высота миграции, метров')
    plt.ylabel('Количество птиц')
    plt.show()


# Функция для обновления статуса
def update_status(filtered_data):
    total_birds = filtered_data['Кол-во птиц в миграции'].sum()
    total_species = filtered_data['Вид птицы'].nunique()
    status_label.config(text=f'Всего птиц: {total_birds}, Всего видов: {total_species}')


def show_statistics():
    bird_type = bird_var.get()
    season = season_var.get()
    filtered_data = data
    if bird_type != "Все виды":
        filtered_data = filtered_data[filtered_data['Вид птицы'] == bird_type]
    if season != "Весь период":
        filtered_data = filtered_data[filtered_data['Сезон'] == season]

    # Получаем текущие данные из таблицы
    table_data = []
    for item in tree.get_children():
        row = tree.item(item, "values")
        table_data.append(row)

    if table_data:
        table_df = pd.DataFrame(table_data, columns=data.columns)

        # Заменяем нечисловые значения в столбцах "Высота миграции, метров" и "Кол-во птиц в миграции" на NaN
        table_df['Высота миграции, метров'] = pd.to_numeric(table_df['Высота миграции, метров'], errors='coerce')
        table_df['Кол-во птиц в миграции'] = pd.to_numeric(table_df['Кол-во птиц в миграции'], errors='coerce')

        # Вычисляем необходимые статистические характеристики
        mean_height = table_df['Высота миграции, метров'].mean()
        median_height = table_df['Высота миграции, метров'].median()
        std_height = table_df['Высота миграции, метров'].std()
        min_height = table_df['Высота миграции, метров'].min()
        max_height = table_df['Высота миграции, метров'].max()
        mode_height = table_df['Высота миграции, метров'].mode()[0]
        q1 = table_df['Высота миграции, метров'].quantile(0.25)
        q3 = table_df['Высота миграции, метров'].quantile(0.75)
        iqr_height = q3 - q1
        cv_height = std_height / mean_height if mean_height != 0 else 0

        # Вычисляем коэффициент корреляции только для числовых значений
        corr_coeff, _ = stats.pearsonr(table_df['Высота миграции, метров'].dropna(), table_df['Кол-во птиц в миграции'].dropna())

        # Создание окна статистики
        stats_window = tk.Toplevel(root)
        stats_window.title("Статистика")

        # Создание фрейма для текстовой статистики
        stats_frame = ttk.Frame(stats_window)
        stats_frame.pack(side=tk.TOP, padx=10, pady=10)

        # Отображение текстовой статистики
        stats_text = f"Среднее значение высоты: {mean_height:.2f} м\n" \
                     f"Медиана высоты: {median_height:.2f} м\n" \
                     f"Стандартное отклонение высоты: {std_height:.2f} м\n" \
                     f"Минимальная высота: {min_height:.2f} м\n" \
                     f"Максимальная высота: {max_height:.2f} м\n" \
                     f"Мода высоты: {mode_height:.2f} м\n" \
                     f"Межквартильный размах высоты: {iqr_height:.2f} м\n" \
                     f"Коэффициент вариации высоты: {cv_height:.2f}\n" \
                     f"Коэффициент корреляции высоты и количества птиц: {corr_coeff:.2f}"
        stats_label = ttk.Label(stats_frame, text=stats_text, font=('Arial', 12))
        stats_label.pack()

        # Создание фрейма для графиков
        plot_frame = ttk.Frame(stats_window)
        plot_frame.pack(side=tk.BOTTOM, padx=10, pady=10)

        # Создание фигуры и областей для графиков
        fig = plt.Figure(figsize=(14, 10))
        height_hist_ax = fig.add_subplot(221)
        bird_count_hist_ax = fig.add_subplot(222)
        scatter_ax = fig.add_subplot(223)
        distance_hist_ax = fig.add_subplot(224)

        # Построение гистограммы распределения высоты миграции
        height_hist_ax.hist(filtered_data['Высота миграции, метров'], bins=70,
                            edgecolor='black')  # Увеличено количество bins
        height_hist_ax.set_title('Распределение высоты миграции', fontsize=10)
        height_hist_ax.set_xlabel('Высота миграции, метров', fontsize=8)
        height_hist_ax.set_ylabel('Частота', fontsize=8)
        height_hist_ax.tick_params(axis='both', which='major', labelsize=8)

        # Построение гистограммы распределения количества птиц в миграции
        bird_count_hist_ax.hist(filtered_data['Кол-во птиц в миграции'], bins=70,
                                edgecolor='black')  # Увеличено количество bins
        bird_count_hist_ax.set_title('Распределение количества птиц в миграции', fontsize=10)
        bird_count_hist_ax.set_xlabel('Количество птиц в миграции', fontsize=8)
        bird_count_hist_ax.set_ylabel('Частота', fontsize=8)
        bird_count_hist_ax.tick_params(axis='both', which='major', labelsize=8)

        # Построение диаграммы рассеяния высоты миграции и количества птиц
        scatter_ax.scatter(filtered_data['Высота миграции, метров'], filtered_data['Кол-во птиц в миграции'])
        scatter_ax.set_title('Диаграмма рассеяния высоты миграции и количества птиц', fontsize=10)
        scatter_ax.set_xlabel('Высота миграции, метров', fontsize=8)
        scatter_ax.set_ylabel('Количество птиц в миграции', fontsize=8)
        scatter_ax.tick_params(axis='both', which='major', labelsize=8)

        # Построение гистограммы распределения длины пролета миграции
        distance_hist_ax.hist(filtered_data['Длина пролёта миграции, метров (расчёт)'], bins=70,
                              edgecolor='black')  # Увеличено количество bins
        distance_hist_ax.set_title('Распределение длины пролета миграции', fontsize=10)
        distance_hist_ax.set_xlabel('Длина пролета миграции, метров', fontsize=8)
        distance_hist_ax.set_ylabel('Частота', fontsize=8)
        distance_hist_ax.tick_params(axis='both', which='major', labelsize=8)
        # Настройка отступов между подграфиками
        fig.subplots_adjust(hspace=0.5, wspace=0.5)  # Увеличение отступов между подграфиками

        # Отображение фигуры в окне
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack()

buttons_frame = ttk.Frame(root)
buttons_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

hist_button = ttk.Button(buttons_frame, text="График высот", command=show_histogram)
hist_button.pack(side=tk.LEFT, padx=10, pady=10)

stat_button = ttk.Button(buttons_frame, text="Статистика", command=show_statistics)
stat_button.pack(side=tk.LEFT, padx=10, pady=10)

# Интерфейс пользователя
status_frame = ttk.Frame(root)
status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

status_label = ttk.Label(status_frame, text='Всего птиц: 0, Всего видов: 0')
status_label.pack(side=tk.LEFT)

version_label = ttk.Label(status_frame, text=current_version)
version_label.pack(side=tk.RIGHT)

toolbar = ttk.Frame(root)
toolbar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

bird_var = tk.StringVar(root)
bird_options = ["Все виды"] + sorted(data['Вид птицы'].unique().tolist())
bird_menu = ttk.OptionMenu(toolbar, bird_var, bird_options[0], *bird_options)
bird_menu.pack(side=tk.LEFT)

season_var = tk.StringVar(root)
season_options = ["Весь период"] + sorted(data['Сезон'].unique().tolist())
season_menu = ttk.OptionMenu(toolbar, season_var, season_options[0], *season_options)
season_menu.pack(side=tk.LEFT)

load_button = ttk.Button(toolbar, text="Обновить", command=filter_data)
load_button.pack(side=tk.LEFT)

table_frame = ttk.Frame(root, relief=tk.RAISED, borderwidth=1)
table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

vertical_scrollbar = ttk.Scrollbar(table_frame, orient="vertical")
horizontal_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal")

tree = ttk.Treeview(table_frame, columns=list(data.columns), show="headings",
                    yscrollcommand=vertical_scrollbar.set,
                    xscrollcommand=horizontal_scrollbar.set)

for col in data.columns:
    tree.heading(col, text=col)
    tree.column(col, anchor='center')

vertical_scrollbar.config(command=tree.yview)
horizontal_scrollbar.config(command=tree.xview)

vertical_scrollbar.pack(side="right", fill="y")
horizontal_scrollbar.pack(side="bottom", fill="x")

tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)


sort_by_column = {}


def sort_treeview_by_column(tree, col, reverse):
    # Попытка определить тип данных в столбце для корректной сортировки
    try:
        # Сначала пытаемся преобразовать все значения столбца к числам
        l = [(pd.to_numeric(tree.set(k, col), errors='coerce'), k) for k in tree.get_children('')]
        if any(val is None for val, k in l):
            # Если есть нечисловые данные, пытаемся интерпретировать их как даты
            l = [(pd.to_datetime(tree.set(k, col), errors='coerce'), k) for k in tree.get_children('')]
            if any(val is None for val, k in l):
                # Если преобразовать в даты не удалось, обрабатываем как строки
                l = [(tree.set(k, col).lower(), k) for k in tree.get_children('')]  # Приводим строки к нижнему регистру для корректной сортировки
    except ValueError:
        # Если преобразование в числа и даты не подходит, считаем значения строками, приводя к нижнему регистру
        l = [(tree.set(k, col).lower(), k) for k in tree.get_children('')]

    # Сортируем с учетом возможности None значений
    l.sort(key=lambda x: (x[0] is None, x[0]), reverse=reverse)

    # Перестановка элементов в соответствии с отсортированным списком
    for index, (val, k) in enumerate(l):
        tree.move(k, '', index)

    # Смена направления сортировки для следующего нажатия
    sort_by_column[col] = not reverse

    # Обновление текста заголовков с указанием направления сортировки
    for column in sort_by_column:
        if column == col:
            order = 'descending' if reverse else 'ascending'
        else:
            order = 'none'
        tree.heading(column, text=column, command=lambda _col=column: sort_treeview_by_column(tree, _col, sort_by_column[_col]))



for col in data.columns:
    sort_by_column[col] = False
    tree.heading(col, text=col, command=lambda _col=col: sort_treeview_by_column(tree, _col, sort_by_column[_col]))




root.iconbitmap('_internal/icon.ico')

img = tk.PhotoImage(file='_internal/icon.png')
root.iconphoto(True, img)
# Запуск основного цикла обработки событий

initialize_table()
root.mainloop()


#
#   pyinstaller --windowed --icon=_internal/icon.ico --add-data "_internal/icon.ico;." --add-data "_internal/icon.png;." --add-data "_internal/botiev2017.xlsx;." --add-data "_internal/botiev2021.xlsx;." Анализ_птиц.py
