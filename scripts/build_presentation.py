#!/usr/bin/env python3
"""Build a Russian Metro Guard pitch deck on the provided LCT 2026 template.

No third-party Python packages are required. The slide artwork is embedded as
Office SVG artwork, which stays sharp at any presentation size. A text outline
is also packaged next to the presentation for editing and reuse.
"""
from __future__ import annotations

import html
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "ЛЦТ2026 Шаблон презентации.pptx"
OUT_DIR = ROOT / "presentation"
DECK = OUT_DIR / "Metro_Guard_ЛЦТ2026.pptx"
OUTLINE = OUT_DIR / "Содержание.md"
SVG_DIR = OUT_DIR / "source"
W, H = 1600, 900
PINK, PALE, LILAC, DARK_PINK = "#FF0053", "#FFD6E4", "#8A83D1", "#FC3777"
INK, PURPLE, WHITE, MUTED = "#1C1D22", "#310F53", "#FFFFFF", "#716879"
BG = "#FFF9FC"


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def text(x, y, value, size=26, color=INK, weight=500, anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" font-family="Montserrat,Arial,sans-serif" '
            f'font-size="{size}" font-weight="{weight}" fill="{color}" '
            f'text-anchor="{anchor}" {extra}>{esc(value)}</text>')


def rect(x, y, w, h, fill=WHITE, rx=22, stroke="none", sw=1):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def line(x1, y1, x2, y2, color=PALE, sw=2, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"{d}/>'


def circle(x, y, r, fill, stroke="none", sw=1):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def wrap_lines(x, y, lines, size=23, color=INK, step=None, weight=450):
    step = step or int(size * 1.43)
    return "".join(text(x, y + i * step, s, size, color, weight) for i, s in enumerate(lines))


class Slide:
    def __init__(self, eyebrow, title, number):
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
                      '<defs><linearGradient id="fade" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#FC3777"/><stop offset="1" stop-color="#FF0053"/></linearGradient></defs>',
                      f'<rect width="{W}" height="{H}" fill="{BG}"/>',
                      '<path d="M0 0H1600V18H0Z" fill="#FF0053"/>',
                      text(82, 91, eyebrow.upper(), 17, PINK, 750, extra="letter-spacing=" + chr(34) + "2.1" + chr(34)),
                      text(82, 160, title, 42, PURPLE, 760),
                      f'<circle cx="1513" cy="82" r="33" fill="{PALE}"/><path d="M1500 82h26m-13-13 13 13-13 13" stroke="{PINK}" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
                      line(82, 827, 1518, 827, "#EADFE8", 2),
                      text(82, 864, "METRO GUARD  ·  LIDAR / ROS 2", 16, MUTED, 650),
                      text(1518, 864, f"ЛЦТ 2026  ·  {number:02d}", 16, MUTED, 650, "end")]

    def add(self, *items):
        self.parts.extend(items)

    def save(self, path):
        path.write_text("\n".join(self.parts + ["</svg>"]), encoding="utf-8")


def pill(x, y, label, fill=PALE, color=PURPLE, width=160):
    return rect(x, y - 27, width, 39, fill, 18) + text(x + width/2, y, label, 17, color, 700, "middle")


def dot_bullet(x, y, label, color=PINK, size=21):
    return circle(x, y - 7, 6, color) + text(x + 22, y, label, size, INK, 500)


def slide_cover():
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
         '<defs><linearGradient id="bg" x1="0" x2="1" y1="1" y2="0"><stop stop-color="#310F53"/><stop offset="1" stop-color="#51106B"/></linearGradient><linearGradient id="hot"><stop stop-color="#FC3777"/><stop offset="1" stop-color="#FF0053"/></linearGradient></defs>',
         '<rect width="1600" height="900" fill="url(#bg)"/>',
         '<circle cx="1370" cy="150" r="330" fill="#520978" opacity=".65"/>',
         '<circle cx="1410" cy="140" r="228" fill="none" stroke="#8A83D1" stroke-width="2" opacity=".55"/>',
         '<circle cx="1410" cy="140" r="170" fill="none" stroke="#8A83D1" stroke-width="2" opacity=".35"/>',
         '<path d="M920 900 1300 420m-80 480 325-480m-30 480 250-480" stroke="#FFD6E4" stroke-width="8" opacity=".8"/>',
         '<path d="M1020 805h470m-417-75h460m-361-75h410m-311-75h365m-267-75h315" stroke="#FC3777" stroke-width="5" opacity=".85"/>',
         f'<rect x="84" y="83" width="338" height="43" rx="21" fill="#FFFFFF" opacity=".12"/>',
         text(105, 112, "ИНЖЕНЕРНОЕ РЕШЕНИЕ  /  2026", 17, "#FFD6E4", 700, extra="letter-spacing="+chr(34)+"2"+chr(34)),
         text(83, 313, "Metro", 91, WHITE, 780), text(83, 413, "Guard", 91, "#FF4D83", 780),
         text(88, 490, "ПОИСК ПРЕПЯТСТВИЙ В ГАБАРИТЕ ПУТИ", 24, "#FFD6E4", 700, extra="letter-spacing="+chr(34)+"1"+chr(34)),
         text(88, 554, "3D LiDAR · геометрия пути · временное подтверждение", 22, WHITE, 450),
         '<rect x="87" y="629" width="540" height="87" rx="17" fill="#FFFFFF" opacity=".1" stroke="#8A83D1"/>',
         text(112, 665, "КОМАНДА / АВТОРЫ", 15, "#FFD6E4", 700),
         text(112, 696, "Добавьте состав команды и контакты", 21, WHITE, 500),
         text(88, 841, "ПРОТОТИП · ОФЛАЙН-АНАЛИЗ · ROS 2", 16, "#FFD6E4", 650),
         '</svg>']
    return "\n".join(p)


def slide_problem():
    s=Slide("01 · ЗАДАЧА", "Опасный объект может быть любым", 2)
    s.add(text(84,221,"В габарите движения важны не класс и название объекта, а его положение относительно пути.",24,MUTED,450))
    s.add(rect(82,278,890,450,WHITE,24,PALE,2), text(119,326,"СИГНАЛ ОТ 3D LiDAR",17,PINK,750))
    # schematic point cloud / rail corridor
    s.add('<path d="M177 635 408 395m140 240 166-240" fill="none" stroke="#8A83D1" stroke-width="8" opacity=".85"/>')
    for x,y in [(189,622),(215,594),(244,565),(274,535),(305,505),(339,473),(376,436),(413,400),(554,622),(576,594),(598,565),(620,535),(642,505),(665,473),(689,436),(711,400)]:
        s.add(line(x,y,x+188,y,"#FFD6E4",3))
    for x,y in [(350,569),(378,540),(400,546),(433,523),(625,550),(650,520),(666,509),(696,485),(737,453),(758,438),(460,471),(481,464),(489,454),(519,435)]:
        s.add(circle(x,y,5,PINK))
    s.add('<path d="M485 455l53-30 26 33-48 30z" fill="#FF0053" opacity=".2" stroke="#FF0053" stroke-width="3"/>')
    s.add(line(790,418,790,629,PURPLE,3,"7 8"), text(812,437,"габарит",17,PURPLE,650), text(812,468,"объект",17,PINK,650))
    s.add(rect(1000,278,519,450,"#FFF1F6",24),text(1040,330,"ЧТО НУЖНО",17,PINK,750))
    s.add(wrap_lines(1040,392,["Найти видимые точки", "постороннего объекта", "и проверить их положение", "относительно рельсового пути."],26,PURPLE,39,650))
    s.add(line(1040,570,1468,570,"#EADFE8",2))
    s.add(wrap_lines(1040,619,["Не пропустить малый предмет.","Не принять инфраструктуру за помеху."],19,INK,34,500))
    s.add(text(1040,696,"ЦЕЛЬ — ВЫХОД ДЛЯ ОПЕРАТОРА",15,MUTED,700))
    return "\n".join(s.parts+["</svg>"])


def slide_team():
    s=Slide("02 · КОМАНДА", "Сильная сторона — проверяемость решения", 3)
    s.add(text(84,220,"Этот слайд оставлен для обязательных данных команды: имена и контакты нельзя достоверно заполнить по репозиторию.",21,MUTED,450))
    cards=[("КАПИТАН","ФИО · специальность","Контакт: заполнить"),("РАЗРАБОТКА","ФИО · роль в команде","Контакт: заполнить"),("ДАННЫЕ И ТЕСТЫ","ФИО · роль в команде","Контакт: заполнить"),("ИНТЕГРАЦИЯ","ФИО · роль в команде","Контакт: заполнить")]
    for i,(a,b,c) in enumerate(cards):
        x=82+i*363
        s.add(rect(x,280,335,250,WHITE,22,PALE,2),circle(x+37,328,9,[PINK,LILAC,DARK_PINK,PURPLE][i]),text(x+60,335,a,16,PINK,750),text(x+26,402,b,22,PURPLE,650),text(x+26,455,c,17,MUTED,500),line(x+26,485,x+305,485,"#EADFE8",1))
    s.add(rect(82,574,1436,180,PURPLE,22),text(119,622,"ВЫЗОВ ДЛЯ КОМАНДЫ",16,"#FFD6E4",750))
    s.add(wrap_lines(119,671,["Определить помеху по разреженному облаку точек в сложном тоннельном фоне;", "проверить геометрию габарита и сохранить воспроизводимый путь от bag до результата."],22,WHITE,34,500))
    return "\n".join(s.parts+["</svg>"])


def slide_solution():
    s=Slide("03 · РЕШЕНИЕ", "Metro Guard: от облака точек до понятного результата", 4)
    blocks=[("01","ВХОД","ROS 2 bag / PointCloud2"),("02","ПУТЬ","Ось и поверхность по рельсам"),("03","ГАБАРИТ","Кандидаты внутри коридора"),("04","ПОДТВЕРЖДЕНИЕ","Группировка и история"),("05","РЕЗУЛЬТАТ","JSON · просмотр · ROS 2")]
    for i,(n,h,b) in enumerate(blocks):
        x=82+i*293
        s.add(rect(x,320,263,235,WHITE,20,PALE,2),circle(x+36,361,22,"#FFD6E4"),text(x+36,368,n,14,PINK,750,"middle"),text(x+25,430,h,17,PURPLE,750),wrap_lines(x+25,475,[b],18,MUTED,27,500))
        if i<4:
            s.add(f'<path d="M{x+267} 434h23m-9-9 9 9-9 9" stroke="#FF0053" fill="none" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
    s.add(rect(82,625,1436,114,"#FFF0F6",20),text(114,670,"Геометрический baseline",23,PURPLE,730),text(456,670,"Без обученной нейросети; каждый этап можно повторить, настроить и проверить.",20,INK,500))
    s.add(text(114,710,"Интенсивность, имена файлов и порядок искусственных объектов детектору не передаются.",16,MUTED,500))
    return "\n".join(s.parts+["</svg>"])


def slide_data():
    s=Slide("04 · ДАННЫЕ", "Установка известна; полный контур поезда — пока нет", 5)
    stats=[("3 998","кадров в 7 bag"),("1 510","кадров нового сценария"),("10","искусственных объектов")]
    for i,(v,lbl) in enumerate(stats):
        x=82+i*480
        s.add(rect(x,222,438,122,WHITE,20,PALE,2),text(x+28,282,v,40,PINK,780),text(x+178,282,lbl,19,PURPLE,600))
    s.add(rect(82,386,694,350,PURPLE,22),text(122,435,"ПОЗИЦИЯ LiDAR",17,"#FFD6E4",750))
    s.add(text(122,513,"1,075 м",43,WHITE,760),text(122,551,"над головкой рельса",19,"#FFD6E4",500))
    s.add(text(122,625,"По центру состава",25,WHITE,700))
    s.add(text(122,681,"Из слов заказчика; отдельного TF/полной калибровки нет.",16,"#E8DCF0",450))
    s.add(rect(804,386,714,350,WHITE,22,PALE,2),text(843,435,"СЦЕНАРИЙ ПРОВЕРКИ",17,PINK,750))
    s.add(wrap_lines(843,488,["Крупные и малые объекты;", "центр, край и вне габарита;", "предметы на рельсе и подвесе."],22,PURPLE,38,650))
    s.add(line(843,626,1473,626,"#EADFE8",2))
    s.add(text(843,671,"Шаг «≈ 100 м» — приблизительный, не калибровка дальности.",17,MUTED,500))
    s.add(text(843,708,"Профиль: config/mounted_lidar.json",16,PINK,650))
    return "\n".join(s.parts+["</svg>"])


def slide_method():
    s=Slide("05 · АЛГОРИТМ", "Как облако превращается в гипотезу препятствия", 6)
    steps=[("01","Декодировать XYZ","Поля PointCloud2; проверка точек."),("02","Найти путь","Оценка rail-guided поверхности."),("03","Проверить объём","Проекция точек внутрь расчётного коридора."),("04","Собрать кластеры","Соседство, размер и фильтры шума."),("05","Подтвердить во времени","Сопоставление наблюдений между кадрами."),("06","Опубликовать статус","obstacle / candidate / unknown / no_obstacle_observed.")]
    for i,(n,h,b) in enumerate(steps):
        col=i%3; row=i//3; x=82+col*488; y=235+row*236
        s.add(rect(x,y,455,196,WHITE,19,PALE,2),rect(x+22,y+24,54,43,"#FFF0F6",14),text(x+49,y+53,n,15,PINK,760,"middle"),text(x+96,y+53,h,19,PURPLE,720),wrap_lines(x+24,y+112,[b],17,MUTED,26,500))
    s.add(text(86,736,"Статус “no_obstacle_observed” не доказывает, что путь свободен: вывод зависит от видимости и геометрических предположений.",16,MUTED,500))
    return "\n".join(s.parts+["</svg>"])


def slide_geometry():
    s=Slide("06 · ГАБАРИТ И КОНФИГУРАЦИЯ", "Положение рельсов оценивается автоматически", 7)
    s.add(rect(82,226,744,492,WHITE,22,PALE,2))
    s.add(text(120,270,"УПРОЩЁННАЯ 3D-СХЕМА",16,PINK,750))
    s.add('<path d="M220 658 363 391m188 267 103-267" fill="none" stroke="#8A83D1" stroke-width="10"/><path d="M256 590h354m-309-75h325m-278-74h295m-250-74h266" stroke="#FFD6E4" stroke-width="5" fill="none"/>')
    s.add('<path d="M347 562 419 405l119 0 63 157z" fill="#FF0053" opacity=".1" stroke="#FF0053" stroke-width="3" stroke-dasharray="9 8"/>')
    for x,y in [(327,522),(352,487),(394,484),(417,454),(552,494),(579,461),(430,382),(610,434),(699,376),(267,565),(540,530)]: s.add(circle(x,y,6,PINK))
    s.add(text(220,690,"X вперёд  ·  Y влево  ·  Z вверх",16,MUTED,600))
    s.add(rect(854,226,664,492,"#FFF1F6",22))
    s.add(text(891,274,"НАСТРОЙКИ ПРОФИЛЯ",16,PINK,750))
    s.add(text(891,343,"1,075 м",34,PURPLE,760),text(1090,342,"опорная высота LiDAR",18,INK,500))
    s.add(line(891,369,1479,369,"#EADFE8",2))
    s.add(text(891,421,"0,10 м",28,PURPLE,720),text(1060,419,"минимальная высота",17,INK,500))
    s.add(text(891,486,"0,12 м",28,PURPLE,720),text(1060,484,"неопределённость края",17,INK,500))
    s.add(line(891,514,1479,514,"#EADFE8",2))
    s.add(wrap_lines(891,558,["Высота используется как начальная опора.","Профиль не заменяет полную трансформацию", "LiDAR ↔ состав и утверждённый контур."],17,INK,30,500))
    s.add(text(891,685,"Ширина 1,45 м — предварительное допущение.",16,PINK,700))
    return "\n".join(s.parts+["</svg>"])


def slide_scenario():
    s=Slide("07 · ПРОВЕРКА НОВОГО BAG", "Настроили чувствительность к низкому предмету", 8)
    s.add(text(85,215,"10 контрольных кадров · point matching / визуальная проверка · не независимая разметка всего проезда",19,MUTED,500))
    s.add(rect(82,251,880,450,WHITE,20,PALE,2))
    s.add(text(117,298,"СОПОСТАВЛЕНИЕ НА КОНТРОЛЬНЫХ КАДРАХ",16,PINK,750))
    s.add(text(356,360,"Исходный профиль",17,MUTED,650,"middle"),text(634,360,"Профиль LiDAR",17,MUTED,650,"middle"))
    # paired detection matrix, objects 1-10
    s.add(text(125,400,"№ объекта",15,MUTED,650))
    for i in range(10):
        y=432+i*24
        s.add(text(141,y,str(i+1),15,INK,550))
        base=i!=8
        s.add(circle(356,y-5,7,LILAC if base else "#E8E2E8"))
        s.add(circle(634,y-5,7,PINK))
    s.add(line(234,412,234,680,"#EEE5EC",1),text(356,690,"9 / 10",17,PURPLE,750,"middle"),text(634,690,"10 / 10",17,PINK,750,"middle"))
    s.add(rect(991,251,527,450,PURPLE,20),text(1030,298,"ЧТО ИЗМЕНИЛИ",16,"#FFD6E4",750))
    s.add(text(1030,377,"№ 9",33,WHITE,760),text(1122,375,"длинный низкий предмет",17,"#FFD6E4",550))
    s.add(text(1030,421,"на рельсах: пропуск → подтверждён",18,WHITE,650))
    s.add(line(1030,458,1477,458,"#8A83D1",2))
    s.add(wrap_lines(1030,502,["2 объекта, описанных как внешние,", "остались неоднозначными: их точки", "попадают в предварительный контур."],17,WHITE,29,500))
    s.add(text(1030,632,"Точность 10/10 не заявляется.",18,"#FFD6E4",750))
    s.add(text(1030,671,"Источник: контрольные кадры bag, не события.",14,"#E5D6EE",500))
    return "\n".join(s.parts+["</svg>"])


def slide_evidence():
    s=Slide("08 · ИЗМЕРЕНИЯ", "Интеграция проверена отдельно от точности", 9)
    data=[("20","автоматических тестов пройдено"),("201 / 201","ROS bag-сообщений обработано"),("0","вытеснений очереди в финальном ROS-прогоне")]
    for i,(val,desc) in enumerate(data):
        x=82+i*480
        s.add(rect(x,231,438,174,WHITE,21,PALE,2),text(x+28,300,val,35,PINK,780),wrap_lines(x+28,354,[desc],16,PURPLE,23,600))
    s.add(rect(82,443,681,266,"#FFF0F6",22),text(120,493,"OFFLINE · НОВЫЙ BAG",17,PINK,750))
    s.add(text(120,556,"43,6 / 62,7 мс",32,PURPLE,760),text(120,591,"p50 / p95 времени ядра",18,INK,550))
    s.add(text(120,641,"Максимум: 115,3 мс",17,MUTED,600),text(120,678,"Локально · параллельные прогоны · без real-time гарантии",15,MUTED,450))
    s.add(rect(805,443,713,266,PURPLE,22),text(844,493,"ROS 2 · PLAYBACK",17,"#FFD6E4",750))
    s.add(text(844,556,"62,9 мс",34,WHITE,760),text(1000,555,"p95 callback → результат",18,"#FFD6E4",550))
    s.add(text(844,616,"Проверены: сообщения, облака, маркеры и watchdog.",17,WHITE,500))
    s.add(text(844,673,"Один bag; Docker/Linux ARM64 — не целевой стенд.",15,"#E5D6EE",500))
    return "\n".join(s.parts+["</svg>"])


def slide_quality():
    s=Slide("09 · ЧЕСТНАЯ ОЦЕНКА", "Что доказано — и что ещё предстоит доказать", 10)
    s.add(rect(82,224,681,468,"#F1FAF5",22),text(124,275,"ПОДТВЕРЖДЕНО ТЕКУЩИМИ ПРОВЕРКАМИ",16,"#24764B",750))
    for i,t in enumerate(["Декодирование предоставленных bag.","Повторяемый offline-проход и экспорт.","20 тестов ядра и интеграционная ROS 2 проверка.","Исправлено обнаружение одного низкого объекта.","Браузерный просмотр кадров и ручная разметка."]): s.add(dot_bullet(128,340+i*61,t,"#2E9660",18))
    s.add(rect(805,224,713,468,"#FFF0F6",22),text(847,275,"НЕ ЯВЛЯЕТСЯ МЕТРИКОЙ КАЧЕСТВА",16,PINK,750))
    for i,t in enumerate(["Precision / recall без ground truth неизвестны.","Контур поезда и полная LiDAR-калибровка отсутствуют.","Ложные тревоги на инфраструктуре не оценены независимо.","Не проверены дальность и скрытые проезды.","ROS bag playback ≠ живой LiDAR и безопасность торможения."]): s.add(dot_bullet(851,340+i*61,t,PINK,17))
    s.add(rect(82,724,1436,64,PURPLE,15),text(112,765,"Следующий обязательный шаг: утвердить контур габарита и размечать отложенные проезды независимо.",19,WHITE,650))
    return "\n".join(s.parts+["</svg>"])


def slide_product():
    s=Slide("10 · ПРИМЕНЕНИЕ", "Продуктовая гипотеза: от разбора записи к пилоту на составе", 11)
    cards=[("01 · АНАЛИЗ","Офлайн-разбор ROS 2 bag","Python CLI · выбор topic · JSONL"),("02 · ПРОСМОТР","3D / сверху / сбоку","Шкала кадров · детекции · ручные метки"),("03 · ИНТЕГРАЦИЯ","ROS 2 Humble узел","PointCloud2 · статус · маркеры RViz")]
    for i,(a,b,c) in enumerate(cards):
        x=82+i*480
        s.add(rect(x,242,438,257,WHITE,21,PALE,2),text(x+28,289,a,16,PINK,750),text(x+28,354,b,24,PURPLE,700),wrap_lines(x+28,412,[c],17,MUTED,26,500))
    s.add(rect(82,548,1436,190,"#FFF0F6",22),text(119,594,"ВЕБ-ДЕПЛОЙ",17,PINK,750))
    s.add(text(119,651,"Docker Compose  ·  Nginx  ·  Ubuntu 24.04",22,PURPLE,700))
    s.add(text(119,698,"Серверный сайт показывает экспортированные результаты; обработку bag запускает CLI или отдельный worker.",17,INK,500))
    s.add(text(1180,651,"2 GB RAM · 20 GB диск",17,MUTED,650))
    s.add(rect(82,759,1436,47,PURPLE,13),text(105,790,"Гипотеза внедрения: пилот у метрополитена / интегратора; заказчик и коммерческая модель ещё не проверены.",15,WHITE,550))
    return "\n".join(s.parts+["</svg>"])


def slide_roadmap():
    s=Slide("11 · ПЛАН РАЗВИТИЯ", "Четыре шага от прототипа к оценке на стенде", 12)
    steps=[("01","Калибровка","Получить контур поезда;" ,"проверить оси, TF и углы."),("02","Разметка","Добавить независимые" ,"событийные метки и split."),("03","Метрики","Измерить precision/recall," ,"ложные тревоги и дальность."),("04","Стенд","Проверить Intel/Ubuntu/" ,"ROS 2 и живой LiDAR.")]
    for i,(n,h,l1,l2) in enumerate(steps):
        x=82+i*363
        s.add(rect(x,267,335,305,WHITE,22,PALE,2),circle(x+42,316,23,"#FFF0F6"),text(x+42,323,n,15,PINK,750,"middle"),text(x+27,389,h,24,PURPLE,720),text(x+27,448,l1,18,INK,500),text(x+27,480,l2,18,INK,500))
        if i<3:s.add(f'<path d="M{x+338} 407h24m-8-8 8 8-8 8" stroke="#FF0053" fill="none" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
    s.add(rect(82,627,1436,112,PURPLE,20),text(116,675,"ГОТОВНОСТЬ СЕЙЧАС",15,"#FFD6E4",750),text(116,713,"Демонстрация и воспроизводимый анализ — да.",21,WHITE,650),text(772,713,"Автономная система безопасности — нет.",21,"#FFD6E4",650))
    return "\n".join(s.parts+["</svg>"])


def slide_close():
    p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<defs><linearGradient id="bg" x1="0" x2="1" y1="1" y2="0"><stop stop-color="#310F53"/><stop offset="1" stop-color="#520978"/></linearGradient></defs>',
       '<rect width="1600" height="900" fill="url(#bg)"/>',
       '<circle cx="1315" cy="465" r="270" fill="none" stroke="#8A83D1" stroke-width="2" opacity=".7"/>',
       '<circle cx="1315" cy="465" r="207" fill="none" stroke="#8A83D1" stroke-width="2" opacity=".45"/>',
       '<path d="M1035 790 1164 144m110 646 44-646m113 646 34-646" stroke="#FFD6E4" stroke-width="7" opacity=".8"/>',
       '<path d="M1080 700h365m-348-95h370m-330-95h360m-307-95h349" stroke="#FF0053" stroke-width="5" opacity=".85"/>',
       text(87,116,"METRO GUARD  ·  LЦТ 2026",18,"#FFD6E4",700,extra="letter-spacing="+chr(34)+"2"+chr(34)),
       text(82,312,"Следующий шаг",57,WHITE,780),text(84,393,"— измерить качество на правильных данных",30,"#FF4D83",650),
       text(88,504,"Контур габарита",20,WHITE,600),text(88,544,"+ независимая разметка",20,"#FFD6E4",500),
       text(88,632,"Вопросы?",23,WHITE,700),text(88,680,"Контакты команды — добавьте перед выступлением.",18,"#E8DCF0",450),
       text(88,838,"ПРОТОТИП ДЛЯ АНАЛИЗА · НЕ СРЕДСТВО УПРАВЛЕНИЯ ПОЕЗДОМ",15,"#FFD6E4",650),'</svg>']
    return "\n".join(p)


SLIDES = [slide_cover(), slide_problem(), slide_team(), slide_solution(), slide_data(), slide_method(),
          slide_geometry(), slide_scenario(), slide_evidence(), slide_quality(), slide_product(), slide_roadmap(), slide_close()]

OUTLINE_TEXT = """# Metro Guard — содержание презентации\n\nПрезентация сделана по шаблону «ЛЦТ2026 Шаблон презентации.pptx». Ниже — текст слайдов, который удобно редактировать и использовать для репетиции.\n\n## 1. Metro Guard\nПоиск препятствий в габарите пути по 3D LiDAR. Геометрия пути, временное подтверждение. Поля состава команды и контактов нужно заполнить перед выступлением.\n\n## 2. Задача\nИскать любой потенциально опасный посторонний объект относительно габарита движения, не ограничиваясь заранее известными классами предметов.\n\n## 3. Команда\nРедактируемые поля капитана, участников, ролей и контактов оставлены для заполнения. Сложность: выделять малые препятствия на фоне тоннельной инфраструктуры и не путать их с объектами вне габарита.\n\n## 4. Решение\nROS 2 bag / PointCloud2 → оценка пути → расчётный габарит → кластеризация точек → подтверждение во времени → JSON, web-viewer или ROS 2. Геометрический baseline, без обученной нейросети.\n\n## 5. Данные и установка\n7 bag, 3 998 кадров суммарно; новый сценарий — 1 510 кадров, 10 объектов. По сообщению поставщика: LiDAR установлен в центре состава на высоте 1,075 м над головкой рельса. Интервал около 100 м приблизителен.\n\n## 6. Алгоритм\nДекодирование XYZ; оценка рельсового пути; отбор точек внутри расчётного объёма; кластеризация; временная ассоциация; выдача статуса. Статус no_obstacle_observed не гарантирует отсутствие помехи.\n\n## 7. Геометрия\nПрофиль config/mounted_lidar.json: rail_guided, опора высоты 1,075 м, min_height=0,10 м, запас неопределённости 0,12 м. Ширина габарита 1,45 м — предварительное предположение, не утверждённая калибровка.\n\n## 8. Новый bag\nНа десяти проверочных кадрах: исходный профиль сопоставил точки детекции с 9 объектами, mounted_lidar — с 10; дополнительный — низкий предмет на рельсах. Это point matching контрольных кадров, не precision/recall. Два объекта, обозначенных как находящиеся вне габарита, остались неоднозначными с предварительным контуром.\n\n## 9. Измерения\n20 автоматических тестов. ROS bag playback: 201 из 201 сообщений, без вытеснения очереди в финальном прогоне; p95 callback→result 62,9 мс. Новый bag: p50/p95 ядра 43,6/62,7 мс, максимум 115,3 мс локально при параллельных прогонах. Эти проверки не обещают real-time на целевом стенде.\n\n## 10. Ограничения\nНет независимой разметки, утверждённого контура состава и полной LiDAR-калибровки; точность, дальность и ложные тревоги независимо не измерены; не проверены скрытые проезды и живой LiDAR на целевом стенде. Проект не управляет торможением.\n\n## 11. Применение\nОфлайн CLI для ROS 2 bag, web-viewer для 3D-просмотра и ручной разметки, ROS 2 Humble узел с PointCloud2 и визуализацией RViz. Облегчённый статический веб-деплой на Docker Compose / Nginx / Ubuntu 24.04.\n\n## 12. План\nПолучить чертёж/контур и проверенную калибровку; разметить события и подготовить независимый hold-out; измерить precision/recall, ложные тревоги и дальность; проверить скорость и живой поток на целевом стенде.\n\n## 13. Закрытие\nСледующий шаг — независимая оценка по верному контуру и размеченным проездам. Контакты команды следует добавить перед выступлением.\n\n## Примечание о достоверности\nЧисла и ограничения согласованы с `docs/FAKE_SCENARIO_RESULTS.md`, `docs/EXPERIMENTS.md` и `docs/NEW_DATA.md`. Число «10 из 10» относится только к сопоставлению в десяти выбранных контрольных кадрах нового bag; оно не означает 100% precision, recall или точность определения границы габарита.\n"""


OUTLINE_TEXT = OUTLINE_TEXT.replace("## 11. Применение", "## 11. Применение и продуктовая гипотеза")
OUTLINE_TEXT = OUTLINE_TEXT.replace(
    "Ниже — текст слайдов, который удобно редактировать и использовать для репетиции.",
    "Ниже — текст слайдов, который удобно редактировать и использовать для репетиции.\n\n"
    "Публичные ссылки: [код проекта](https://github.com/kurorodev/lct2026_metro) · "
    "[веб-демонстрация](http://111.88.155.2/). Чтобы запустить проект локально, "
    "см. [инструкцию в README](../README.md#локальный-запуск).",
)
OUTLINE_TEXT = OUTLINE_TEXT.replace(
    "\n## 12. План",
    "\nГипотеза внедрения: пилот у метрополитена или интегратора; спрос и коммерческая модель пока не проверены.\n\n## 12. План",
)


def write_svgs() -> list[Path]:
    SVG_DIR.mkdir(parents=True, exist_ok=True)
    svgs=[]
    for i,svg in enumerate(SLIDES,1):
        source=SVG_DIR/f"slide-{i:02d}.svg"
        source.write_text(svg,encoding="utf-8")
        svgs.append(source)
    return svgs


def transparent_png() -> bytes:
    """Valid transparent 1x1 compatibility preview; Office uses the SVG extension."""
    import struct, zlib
    def chunk(kind: bytes, payload: bytes) -> bytes:
        body=kind+payload
        return struct.pack(">I",len(payload))+body+struct.pack(">I",zlib.crc32(body)&0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR",struct.pack(">IIBBBBB",1,1,8,6,0,0,0))
            + chunk(b"IDAT",zlib.compress(b"\x00\xff\xf9\xfc\x00")) + chunk(b"IEND",b""))


def build_pptx(svgs: list[Path]):
    P="http://schemas.openxmlformats.org/presentationml/2006/main"
    A="http://schemas.openxmlformats.org/drawingml/2006/main"
    R="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    ASVG="http://schemas.microsoft.com/office/drawing/2016/SVG/main"
    PR="http://schemas.openxmlformats.org/package/2006/relationships"
    CT="http://schemas.openxmlformats.org/package/2006/content-types"
    ET.register_namespace("p",P); ET.register_namespace("a",A); ET.register_namespace("r",R)
    ET.register_namespace("",PR)
    base=TEMPLATE if TEMPLATE.exists() else DECK
    with zipfile.ZipFile(base,"r") as zin:
        items={name:zin.read(name) for name in zin.namelist()}
    pres=ET.fromstring(items["ppt/presentation.xml"])
    idlist=pres.find(f"{{{P}}}sldIdLst")
    allids=list(idlist)
    # Reuse the first 13 package parts, remove the instructional/appendix slides from the show.
    keep=allids[:len(svgs)]
    for child in list(idlist): idlist.remove(child)
    for child in keep: idlist.append(child)
    items["ppt/presentation.xml"]=ET.tostring(pres,encoding="utf-8",xml_declaration=True)
    rels=ET.fromstring(items["ppt/_rels/presentation.xml.rels"])
    relmap={e.attrib["Id"]:e.attrib["Target"] for e in rels}
    slide_parts=[]
    for i,ident in enumerate(keep,1):
        rid=ident.attrib[f"{{{R}}}id"]
        target=relmap[rid]
        slide_parts.append(target.replace("../", "ppt/") if target.startswith("../") else "ppt/"+target)
    # Add a full-slide artwork image above the template decoration on each page.
    for i,(part,svg) in enumerate(zip(slide_parts,svgs),1):
        slide=ET.fromstring(items[part])
        tree=slide.find(f"{{{P}}}cSld/{{{P}}}spTree")
        # Keep only the required non-visual group and its transform.
        for child in list(tree):
            if child.tag not in (f"{{{P}}}nvGrpSpPr",f"{{{P}}}grpSpPr"):
                tree.remove(child)
        pic=ET.SubElement(tree,f"{{{P}}}pic")
        nv=ET.SubElement(pic,f"{{{P}}}nvPicPr")
        ET.SubElement(nv,f"{{{P}}}cNvPr",{"id":"2","name":f"Metro Guard slide {i}","descr":f"Slide {i}; Russian-language Metro Guard project presentation"})
        locks=ET.SubElement(ET.SubElement(nv,f"{{{P}}}cNvPicPr"),f"{{{A}}}picLocks",{"noChangeAspect":"1"})
        ET.SubElement(nv,f"{{{P}}}nvPr")
        fill=ET.SubElement(pic,f"{{{P}}}blipFill")
        blip=ET.SubElement(fill,f"{{{A}}}blip",{f"{{{R}}}embed":"rIdMetroFallback"})
        extlist=ET.SubElement(blip,f"{{{A}}}extLst")
        extension=ET.SubElement(extlist,f"{{{A}}}ext",{"uri":"{96E0A9C8-4F8B-4D6B-86EA-88D5DC510E1E}"})
        ET.SubElement(extension,f"{{{ASVG}}}svgBlip",{f"{{{R}}}embed":"rIdMetroArt"})
        stretch=ET.SubElement(fill,f"{{{A}}}stretch"); ET.SubElement(stretch,f"{{{A}}}fillRect")
        sppr=ET.SubElement(pic,f"{{{P}}}spPr")
        xf=ET.SubElement(sppr,f"{{{A}}}xfrm"); ET.SubElement(xf,f"{{{A}}}off",{"x":"0","y":"0"})
        ET.SubElement(xf,f"{{{A}}}ext",{"cx":"12192000","cy":"6858000"})
        geom=ET.SubElement(sppr,f"{{{A}}}prstGeom",{"prst":"rect"}); ET.SubElement(geom,f"{{{A}}}avLst")
        slide_rel=f"ppt/slides/_rels/{Path(part).name}.rels"
        relroot=ET.fromstring(items[slide_rel])
        for child in list(relroot):
            if child.attrib.get("Id") in ("rIdMetroArt","rIdMetroFallback"): relroot.remove(child)
        ET.SubElement(relroot,f"{{{PR}}}Relationship",{"Id":"rIdMetroFallback","Type":f"{R}/image","Target":f"../media/metro_guard_{i:02d}.png"})
        ET.SubElement(relroot,f"{{{PR}}}Relationship",{"Id":"rIdMetroArt","Type":f"{R}/image","Target":f"../media/metro_guard_{i:02d}.svg"})
        items[slide_rel]=ET.tostring(relroot,encoding="utf-8",xml_declaration=True)
        items[part]=ET.tostring(slide,encoding="utf-8",xml_declaration=True)
        items[f"ppt/media/metro_guard_{i:02d}.png"]=transparent_png()
        items[f"ppt/media/metro_guard_{i:02d}.svg"]=svg.read_bytes()
    types=ET.fromstring(items["[Content_Types].xml"])
    if not any(el.attrib.get("Extension")=="png" for el in types):
        ET.SubElement(types,f"{{{CT}}}Default",{"Extension":"png","ContentType":"image/png"})
    if not any(el.attrib.get("Extension")=="svg" for el in types):
        ET.SubElement(types,f"{{{CT}}}Default",{"Extension":"svg","ContentType":"image/svg+xml"})
    ET.register_namespace("",CT)
    items["[Content_Types].xml"]=ET.tostring(types,encoding="utf-8",xml_declaration=True)
    OUT_DIR.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(DECK,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=7) as zout:
        for name,data in items.items(): zout.writestr(name,data)


def main():
    if not TEMPLATE.exists() and not DECK.exists():
        raise SystemExit(f"Не найден шаблон или ранее собранная презентация: {TEMPLATE}")
    svgs=write_svgs()
    build_pptx(svgs)
    OUTLINE.write_text(OUTLINE_TEXT,encoding="utf-8")
    with zipfile.ZipFile(DECK) as z:
        ppt_slides=sum(1 for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
        media=sum(1 for n in z.namelist() if n.startswith("ppt/media/metro_guard_") and n.endswith(".png"))
    print(f"Готово: {DECK.relative_to(ROOT)} · {len(SLIDES)} слайдов · {DECK.stat().st_size/1e6:.1f} МБ")
    print(f"Текст и пояснения: {OUTLINE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
