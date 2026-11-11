import flet as ft
import flet_webview as fwv
from datetime import date, timedelta
from collections import defaultdict

BG = "#F5FAF6"
DARK = "#14362B"
GREEN = "#207B51"
MINT = "#DDF2E5"
WHITE = "#FFFFFF"
MUTED = "#60776C"
CATEGORIES = ["Groceries", "Restaurants", "Transport", "Shopping", "Entertainment", "Healthcare", "Other"]
COLORS = ["#247D55", "#49A878", "#88C5A1", "#B4DCC3", "#74A6A1", "#C8B4DB", "#A8B5AE"]


def main(page: ft.Page):
    page.title = "SpendSense"
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    today = date.today()
    transactions = [
        {"merchant": "Tesco", "amount": 23.40, "category": "Groceries", "date": today},
        {"merchant": "Cafe", "amount": 8.90, "category": "Restaurants", "date": today - timedelta(days=1)},
        {"merchant": "Train ticket", "amount": 12.50, "category": "Transport", "date": today - timedelta(days=3)},
        {"merchant": "Bookshop", "amount": 18.00, "category": "Shopping", "date": today - timedelta(days=8)},
        {"merchant": "Cinema", "amount": 11.99, "category": "Entertainment", "date": today - timedelta(days=20)},
        {"merchant": "Pharmacy", "amount": 7.20, "category": "Healthcare", "date": today - timedelta(days=42)},
    ]
    screen = "Home"
    period = "Month"
    demo = True

    def txt(value, size=15, color=DARK, bold=False):
        return ft.Text(str(value), size=size, color=color,
                       weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL)

    def panel(*items, color=WHITE):
        return ft.Container(
            content=ft.Column(controls=list(items), spacing=12),
            bgcolor=color, border_radius=18, padding=18,
        )

    def heading(title, subtitle=None):
        items = [txt(title, 23, DARK, True)]
        if subtitle:
            items.append(txt(subtitle, 12, MUTED))
        return ft.Column(controls=items, spacing=3)

    def filtered():
        if period == "Day":
            return [t for t in transactions if t["date"] == today]
        if period == "Week":
            start = today - timedelta(days=today.weekday())
            return [t for t in transactions if start <= t["date"] <= today]
        if period == "Month":
            return [t for t in transactions if t["date"].year == today.year
                    and t["date"].month == today.month]
        return [t for t in transactions if t["date"].year == today.year]

    def total(rows):
        return sum(t["amount"] for t in rows)

    def switch(name):
        nonlocal screen
        screen = name
        render()

    def choose_period(name):
        nonlocal period
        period = name
        render()

    def clear_sample(e):
        nonlocal demo
        if demo:
            transactions.clear()
            demo = False
            render()

    def remove_transaction(item):
        def action(e):
            nonlocal demo
            transactions.remove(item)
            demo = False
            render()
        return action

    def row_for(item, show_delete=False):
        left = ft.Column(controls=[
            txt(item["merchant"], 15, DARK, True),
            txt(f'{item["category"]} • {item["date"].strftime("%d %b %Y")}', 11, MUTED),
        ], spacing=2, expand=True)
        controls = [left, txt(f'-£{item["amount"]:.2f}', 15, DARK, True)]
        if show_delete:
            controls.append(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE,
                                          icon_color=MUTED,
                                          on_click=remove_transaction(item)))
        return ft.Row(controls=controls, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    def category_totals(rows):
        values = defaultdict(float)
        for item in rows:
            values[item["category"]] += item["amount"]
        return values

    def category_bars(rows):
        values = category_totals(rows)
        biggest = max(values.values(), default=1)
        result = []
        for i, cat in enumerate(CATEGORIES):
            amount = values.get(cat, 0)
            if amount <= 0:
                continue
            result.extend([
                ft.Row(controls=[txt(cat, 13), ft.Container(expand=True),
                                 txt(f'£{amount:.2f}', 13, DARK, True)]),
                ft.ProgressBar(value=amount / biggest, color=COLORS[i], bgcolor=MINT,
                               bar_height=12, border_radius=8),
            ])
        return result or [txt("No spending recorded for this period.", 13, MUTED)]

    def period_buttons():
        return ft.Row(
            controls=[ft.Button(p, on_click=lambda e, x=p: choose_period(x),
                                bgcolor=GREEN if p == period else MINT,
                                color=WHITE if p == period else DARK)
                      for p in ["Day", "Week", "Month", "Year"]],
            spacing=5, wrap=True,
        )

    def home():
        rows = filtered()
        recent = sorted(transactions, key=lambda t: t["date"], reverse=True)[:4]
        return [
            heading("Good to see you!", "Your spending at a glance"),
            panel(
                txt("Snap. Track. Save.", 15, WHITE),
                txt("Scan your receipt", 24, WHITE, True),
                txt("Receipt scanning is coming soon. Add expenses manually for now.", 12, WHITE),
                ft.Button("Add a transaction", on_click=lambda e: switch("Scan"),
                          bgcolor=WHITE, color=GREEN),
                color=GREEN,
            ),
            period_buttons(),
            panel(
                txt(f"Spent this {period.lower()}", 13, MUTED),
                txt(f"£{total(rows):,.2f}", 32, DARK, True),
                ft.Row(controls=[txt(f"{len(rows)} transactions", 12, MUTED),
                                 ft.Container(expand=True),
                                 txt(f"{len(category_totals(rows))} categories tracked", 12, GREEN)]),
            ),
            panel(
                ft.Row(controls=[txt("Spending by category", 17, DARK, True),
                                 ft.Container(expand=True),
                                 ft.TextButton("See all", on_click=lambda e: switch("Categories"))]),
                *category_bars(rows),
            ),
            panel(
                ft.Row(controls=[txt("Recent transactions", 17, DARK, True),
                                 ft.Container(expand=True),
                                 ft.TextButton("View all", on_click=lambda e: switch("History"))]),
                *([row_for(t) for t in recent] or [txt("Nothing logged yet.", 13, MUTED)]),
            ),
        ]

    def add_screen():
        merchant = ft.TextField(label="Shop or merchant", hint_text="e.g. Tesco")
        amount = ft.TextField(label="Amount in pounds", hint_text="e.g. 12.50",
                              keyboard_type=ft.KeyboardType.NUMBER)
        category = ft.Dropdown(label="Category", value="Groceries",
                               options=[ft.DropdownOption(key=c, text=c) for c in CATEGORIES])
        feedback = txt("", 12, GREEN)

        def save(e):
            nonlocal demo
            name = (merchant.value or "").strip()
            try:
                cost = round(float((amount.value or "").strip()), 2)
            except ValueError:
                feedback.value = "Enter a valid amount, such as 12.50."
                page.update()
                return
            if not name or cost <= 0 or cost > 1000000:
                feedback.value = "Enter a merchant and a positive amount."
                page.update()
                return
            if demo:
                transactions.clear()
            transactions.append({"merchant": name, "amount": cost,
                                 "category": category.value or "Other", "date": today})
            demo = False
            switch("Home")

        return [
            heading("Add a transaction", "Keep track of spending in just a few taps"),
            panel(
                txt("Receipt scanner", 20, DARK, True),
                txt("Photo scanning and automatic AI extraction are not connected in this version.", 13, MUTED),
                txt("For now, you can add transactions manually below.", 13, GREEN),
            ),
            panel(txt("New expense", 19, DARK, True), merchant, amount, category,
                  ft.Button("Save transaction", bgcolor=GREEN, color=WHITE, on_click=save),
                  feedback),
        ]

    def receipt_scanner():
        return [
            heading(
                "Scan your receipt",
                "Upload and organise your spending"
            ),
            ft.Container(
                content=fwv.WebView(
                    url="https://apandya-app.github.io/SpendSense/receipt-scanner.html",
                    expand=True,
                ),
                height=650,
            ),
        ]
        
    def history():
        ordered = sorted(transactions, key=lambda t: t["date"], reverse=True)
        return [heading("Transaction history", "Review or remove purchases"),
                panel(*([row_for(t, True) for t in ordered] or
                        [txt("No transactions yet. Add one from Scan.", 13, MUTED)]))]

    def trend_bars():
        if period == "Day":
            days = [today]
        elif period == "Week":
            start = today - timedelta(days=today.weekday())
            days = [start + timedelta(days=i) for i in range(7)]
        elif period == "Month":
            days = [today.replace(day=1) + timedelta(days=i)
                    for i in range((today - today.replace(day=1)).days + 1)]
        else:
            days = [today.replace(month=1, day=1) + timedelta(days=i)
                    for i in range((today - today.replace(month=1, day=1)).days + 1)]
        groups = defaultdict(float)
        for item in transactions:
            if item["date"] in days:
                key = item["date"].strftime("%d %b") if period in ("Day", "Week") else item["date"].strftime("%b")
                groups[key] += item["amount"]
        if period in ("Month", "Year"):
            keys = list(dict.fromkeys(d.strftime("%b") for d in days))
        else:
            keys = [d.strftime("%d %b") for d in days]
        maximum = max(groups.values(), default=1) or 1
        return [ft.Row(controls=[
                    ft.Container(width=55, content=txt(key, 11, MUTED)),
                    ft.ProgressBar(value=groups.get(key, 0) / maximum,
                                   color=GREEN, bgcolor=MINT, expand=True, bar_height=11),
                    ft.Container(width=72, content=txt(f"£{groups.get(key, 0):.2f}", 11, DARK)),
                ]) for key in keys]

    def stats():
        rows = filtered()
        n = len(rows)
        average = total(rows) / n if n else 0
        return [
            heading("Spending insights", "An overview of where your money goes"),
            period_buttons(),
            panel(txt("Total spent", 13, MUTED), txt(f"£{total(rows):,.2f}", 30, DARK, True),
                  txt(f"Average per transaction: £{average:.2f}", 13, MUTED)),
            panel(txt("Spending trend", 18, DARK, True), *trend_bars()),
            panel(txt("Category breakdown", 18, DARK, True), *category_bars(rows)),
            ft.Button("Open categories page", on_click=lambda e: switch("Categories"),
                      bgcolor=MINT, color=DARK),
        ]

    def categories():
        rows = filtered()
        return [heading("Categories", "Understand your spending habits"),
                period_buttons(), panel(*category_bars(rows)),
                ft.Button("Back to insights", on_click=lambda e: switch("Stats"),
                          bgcolor=MINT, color=DARK)]


    
   
    def render():
        sections = {
            "Home": home,
            "Scan": add_screen,
            "Receipt": receipt_scanner,
            "History": history,
            "Stats": stats,
            "Categories": categories,
        }


}
        controls = [
            ft.Row(controls=[txt("SpendSense", 26, DARK, True),
                             ft.Container(expand=True),
                             ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, color=GREEN, size=28)]),
        ]
        if demo:
            controls.append(ft.Container(
                content=ft.Row(controls=[
                    ft.Text("Demo transactions — not your real spending", color=DARK, size=11, expand=True),
                    ft.TextButton("Clear", on_click=clear_sample),
                ]), bgcolor=MINT, border_radius=10, padding=6))
        controls.extend(sections[screen]())
        nav = ft.Row(controls=[
            ft.Button(name, on_click=lambda e, x=name: switch(x),
                      bgcolor=GREEN if screen == name else WHITE,
                      color=WHITE if screen == name else DARK)
            for name in ["Home", "Receipt", "History", "Stats"]
        ], spacing=5, wrap=True, alignment=ft.MainAxisAlignment.CENTER)
        page.clean()
        page.scroll = ft.ScrollMode.ALWAYS
        page.add(
            ft.SafeArea(
                content=ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Column(
                                controls=controls,
                                spacing=16,
                            ),
                            padding=18,
                        ),
                        ft.Container(
                            content=nav,
                            bgcolor=WHITE,
                            padding=10,
                        ),
                    ],
                    spacing=0,
                )
            )
        )
        page.update()


    render()


if __name__ == "__main__":
    ft.run(main)
