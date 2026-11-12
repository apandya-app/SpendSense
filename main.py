import flet as ft
import flet_webview as fwv
import base64
import mimetypes
from collections import defaultdict
from datetime import date, timedelta

# Receiptly - Finance Dashboard and Receipt Scanner

BG = "#F5FAF6"
DARK = "#14362B"
GREEN = "#207B51"
MINT = "#DDF2E5"
WHITE = "#FFFFFF"
MUTED = "#60776C"

CATEGORIES = ["Groceries", "Restaurants", "Transport", "Shopping", "Entertainment", "Healthcare", "Other"]
COLORS = ["#247D55", "#49A878", "#88C5A1", "#B4DCC3", "#74A6A1", "#C8B4DB", "#A8B5AE"]
SCANNER_URL = "https://apandya-app.github.io/SpendSense/receipt-scanner.html"

async def main(page: ft.Page):
    page.title = "Receiptly"
    page.bgcolor = BG
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.scroll = None
    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    import json
    prefs = ft.SharedPreferences()
    STORAGE_KEY = "receiptly.transactions.v1"
    async def save_transactions():
        data = [
            {**t, "date": t["date"].isoformat()}
            for t in transactions
        ]
        return await prefs.set(STORAGE_KEY, json.dumps(data))

    async def load_transactions():
        try:
            saved = await prefs.get(STORAGE_KEY)
        except Exception as err:
            print("Unable to read saved transactions:", err)
            return
        if saved is None:
            return
        try:
            data = json.loads(saved)
            restored = [
                {**t, "date": date.fromisoformat(t["date"])}
                for t in data
            ]
            transactions.clear()
            transactions.extend(restored)
        except (ValueError, TypeError, KeyError):
            print("Could not restore saved transactions")


    today = date.today()
    transactions = []
    screen = "Home"
    period = "Month"

    def txt(value, size=15, color=DARK, bold=False):
        return ft.Text(str(value), size=size, color=color,
                       weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL)

    def panel(*items, color=WHITE):
        return ft.Container(content=ft.Column(controls=list(items), spacing=12),
                            bgcolor=color, border_radius=18, padding=18)

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

    def show_storage_error():
        page.show_dialog(ft.AlertDialog(
            title=ft.Text("Could not save changes"),
            content=ft.Text("Receiptly could not write to this device's storage. Please try again."),
            actions=[ft.TextButton("OK", on_click=lambda e: page.pop_dialog())]
        ))

    def remove_transaction(item):
        async def action(e):
            index = transactions.index(item)
            transactions.pop(index)
            try:
                await save_transactions()
            except Exception as err:
                transactions.insert(index, item)
                print("Transaction deletion failed:", err)
                show_storage_error()
            render()
        return action

    async def remove_all_confirmed(e):
        try:
            await prefs.set(STORAGE_KEY, "[]")
        except Exception as err:
            print("Clear-all failed:", err)
            page.pop_dialog()
            show_storage_error()
            return
        transactions.clear()
        page.pop_dialog()
        render()

    def confirm_remove_all(e):
        if not transactions:
            return
        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Remove all transactions?"),
            content=ft.Text(
                "This deletes all transactions saved in the main Receiptly dashboard on this device. "
                "It does not delete receipts stored separately in the scanner. This cannot be undone."
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: page.pop_dialog()),
                ft.Button("Remove all", bgcolor="#C62828", color=WHITE, on_click=remove_all_confirmed),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        ))

    def row_for(item, show_delete=False):
        left = ft.Column(controls=[
            txt(item["merchant"], 15, DARK, True),
            txt(f'{item["category"]} • {item["date"].strftime("%d %b %Y")}', 11, MUTED)
        ], spacing=2, expand=True)

        controls = [left, txt(f'-£{item["amount"]:.2f}', 15, DARK, True)]
        if show_delete:
            controls.append(ft.IconButton(icon=ft.Icons.DELETE_OUTLINE,
                                          icon_color=MUTED, on_click=remove_transaction(item)))
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
                                 txt(f"£{amount:.2f}", 13, DARK, True)]),
                ft.ProgressBar(value=amount / biggest, color=COLORS[i], bgcolor=MINT,
                               bar_height=12, border_radius=8),
            ])
        return result or [txt("No spending recorded for this period.", 13, MUTED)]

    def period_buttons():
        # Compact filters that remain on one line on a narrow Android screen.
        return ft.Row(
            spacing=4,
            wrap=False,
            controls=[
                ft.Button(
                    p,
                    expand=True,
                    on_click=lambda e, x=p: choose_period(x),
                    bgcolor=GREEN if p == period else MINT,
                    color=WHITE if p == period else DARK,
                    style=ft.ButtonStyle(
                        padding=ft.Padding.symmetric(horizontal=3, vertical=9),
                        text_style=ft.TextStyle(size=12),
                    ),
                )
                for p in ("Day", "Week", "Month", "Year")
            ],
        )

    def home():
        rows = filtered()
        recent = sorted(transactions, key=lambda t: t["date"], reverse=True)[:4]

        return [
            heading("Good to see you!", "Your spending at a glance"),
            panel(
                txt("Snap. Track. Save.", 15, WHITE),
                txt("Scan your receipt", 24, WHITE, True),
                txt("Upload a receipt or add an expense manually.", 12, WHITE),
                ft.Row(
                    spacing=5,
                    wrap=False,
                    controls=[
                        ft.Button("Scan", expand=True,
                                  on_click=lambda e: switch("Receipt"),
                                  bgcolor=WHITE, color=GREEN,
                                  style=ft.ButtonStyle(
                                      padding=ft.Padding.symmetric(horizontal=4, vertical=9),
                                      text_style=ft.TextStyle(size=12),
                                  )),
                        ft.Button("Add", expand=True,
                                  on_click=lambda e: switch("Scan"),
                                  bgcolor=MINT, color=DARK,
                                  style=ft.ButtonStyle(
                                      padding=ft.Padding.symmetric(horizontal=4, vertical=9),
                                      text_style=ft.TextStyle(size=12),
                                  )),
                        ft.Button("My receipts", expand=True,
                                  on_click=lambda e: switch("Library"),
                                  bgcolor=WHITE, color=GREEN,
                                  style=ft.ButtonStyle(
                                      padding=ft.Padding.symmetric(horizontal=2, vertical=9),
                                      text_style=ft.TextStyle(size=11),
                                  )),
                    ],
                ),
                color=GREEN,
            ),
            period_buttons(),
            panel(
                txt(f"Spent this {period.lower()}", 13, MUTED),
                txt(f"£{total(rows):,.2f}", 32, DARK, True),
                ft.Row(controls=[
                    txt(f"{len(rows)} transactions", 12, MUTED),
                    ft.Container(expand=True),
                    txt(f"{len(category_totals(rows))} categories tracked", 12, GREEN),
                ]),
            ),
            panel(
                ft.Row(controls=[
                    txt("Spending by category", 17, DARK, True),
                    ft.Container(expand=True),
                    ft.TextButton("See all", on_click=lambda e: switch("Categories")),
                ]),
                *category_bars(rows),
            ),
            panel(
                ft.Row(controls=[
                    txt("Recent transactions", 17, DARK, True),
                    ft.Container(expand=True),
                    ft.TextButton("View all", on_click=lambda e: switch("History")),
                ]),
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

        async def save(e):
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

            item = {"merchant": name, "amount": cost,
                    "category": category.value or "Other", "date": today}
            transactions.append(item)
            try:
                await save_transactions()
            except Exception as err:
                transactions.remove(item)
                print("Transaction save failed:", err)
                feedback.value = "Could not save the transaction. Please try again."
                page.update()
                return
            switch("Home")

        return [
            heading("Add a transaction", "Log spending manually"),
            ft.Button("Open receipt scanner", on_click=lambda e: switch("Receipt"),
                      bgcolor=MINT, color=DARK),
            panel(txt("New expense", 19, DARK, True), merchant, amount, category,
                  ft.Button("Save transaction", bgcolor=GREEN, color=WHITE, on_click=save),
                  feedback),
        ]

    def receipt_scanner():
        # Android WebView does not always open the HTML file input.
        # Use Flet's native picker, then pass the photo to the existing OCR page.
        scanner_view = fwv.WebView(url=SCANNER_URL, expand=True)
        selection_status = txt("Choose an image from your phone.", 12, MUTED)

        async def choose_image(e):
            selection_status.value = "Opening your phone's photo picker..."
            page.update()
            try:
                selected_files = await file_picker.pick_files(
                    allow_multiple=False,
                    file_type=ft.FilePickerFileType.IMAGE,
                    with_data=True,
                    compression_quality=70,
                )
                if not selected_files:
                    selection_status.value = "No image selected."
                    page.update()
                    return

                selected = selected_files[0]
                image_bytes = selected.bytes
                if not image_bytes:
                    raise ValueError("The selected photo could not be read.")
                if len(image_bytes) > 5 * 1024 * 1024:
                    raise ValueError(
                        "That photo is too large. Please try one under 5 MB."
                    )

                mime = mimetypes.guess_type(selected.name)[0] or "image/jpeg"
                if mime not in ("image/jpeg", "image/png", "image/webp"):
                    raise ValueError(
                        "Please choose a JPG, PNG or WebP photo."
                    )

                encoded = base64.b64encode(image_bytes).decode("ascii")
                # Flet's Android WebView supports running JavaScript in
                # the currently loaded receipt-scanner.html page.
                script = """
                (() => {
                  const encoded = __IMAGE_BYTES_JSON__;
                  const name = __IMAGE_NAME_JSON__;
                  const mime = __IMAGE_MIME_JSON__;
                  const input = document.getElementById('photo');
                  if (!input) throw new Error('Scanner is not ready.');
                  const binary = atob(encoded);
                  const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
                  const file = new File([bytes], name, {type: mime});
                  const transfer = new DataTransfer();
                  transfer.items.add(file);
                  input.files = transfer.files;
                  input.dispatchEvent(new Event('change', {bubbles: true}));
                })();
                """
                script = (
                    script.replace("__IMAGE_BYTES_JSON__", json.dumps(encoded))
                    .replace("__IMAGE_NAME_JSON__", json.dumps(selected.name))
                    .replace("__IMAGE_MIME_JSON__", json.dumps(mime))
                )
                await scanner_view.run_javascript(script)
                selection_status.value = (
                    "Image selected. Tap 'Read receipt' below to scan it."
                )
            except Exception as err:
                print("Native receipt picker failed:", err)
                selection_status.value = (
                    "Could not select that image: " + str(err)
                )
            page.update()

        return [
            heading("Scan your receipt", "Choose an image from your Android phone"),
            ft.Button(
                "Choose photo from phone",
                icon=ft.Icons.FOLDER_OPEN,
                bgcolor=GREEN,
                color=WHITE,
                on_click=choose_image,
            ),
            selection_status,
            ft.Container(
                content=scanner_view,
                height=650,
                bgcolor=WHITE,
                border_radius=12,
            ),
            ft.Button(
                "My saved receipts",
                on_click=lambda e: switch("Library"),
                bgcolor=MINT,
                color=DARK,
            ),
            ft.Button(
                "Enter a transaction manually",
                on_click=lambda e: switch("Scan"),
                bgcolor=MINT,
                color=DARK,
            ),
        ]

    def receipt_library():
        return [
            heading("My receipt library", "Browse your saved receipt photos by category"),
            txt("Photos are saved on this device, separately from your main dashboard.",
                12, MUTED),
            ft.Container(
                content=fwv.WebView(url=SCANNER_URL + "#receipt-library", expand=True),
                height=700, bgcolor=WHITE, border_radius=12,
            ),
            ft.Button("Scan another receipt", on_click=lambda e: switch("Receipt"),
                      bgcolor=MINT, color=DARK),
        ]

    def history():
        ordered = sorted(transactions, key=lambda t: t["date"], reverse=True)
        return [
            heading("Transaction history", "Review or remove purchases"),
            panel(*([row_for(t, True) for t in ordered] or
                    [txt("No transactions yet. Add one manually.", 13, MUTED)])),
        ]

    def trend_bars():
        if period == "Day":
            days = [today]
        elif period == "Week":
            start = today - timedelta(days=today.weekday())
            days = [start + timedelta(days=i) for i in range(7)]
        elif period == "Month":
            start = today.replace(day=1)
            days = [start + timedelta(days=i) for i in range((today - start).days + 1)]
        else:
            start = today.replace(month=1, day=1)
            days = [start + timedelta(days=i) for i in range((today - start).days + 1)]

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
        return [
            ft.Row(controls=[
                ft.Container(width=55, content=txt(key, 11, MUTED)),
                ft.ProgressBar(value=groups.get(key, 0) / maximum,
                               color=GREEN, bgcolor=MINT, expand=True, bar_height=11),
                ft.Container(width=72, content=txt(f"£{groups.get(key, 0):.2f}", 11, DARK)),
            ]) for key in keys
        ]

    def stats():
        rows = filtered()
        n = len(rows)
        average = total(rows) / n if n else 0

        return [
            heading("Spending insights", "An overview of where your money goes"),
            period_buttons(),
            panel(
                txt("Total spent", 13, MUTED),
                txt(f"£{total(rows):,.2f}", 30, DARK, True),
                txt(f"Average per transaction: £{average:.2f}", 13, MUTED),
            ),
            panel(txt("Spending trend", 18, DARK, True), *trend_bars()),
            panel(txt("Category breakdown", 18, DARK, True), *category_bars(rows)),
            ft.Button("Open categories page", on_click=lambda e: switch("Categories"),
                      bgcolor=MINT, color=DARK),
        ]

    def categories():
        rows = filtered()
        return [
            heading("Categories", "Understand your spending habits"),
            period_buttons(),
            panel(*category_bars(rows)),
            ft.Button("View saved receipt photos", on_click=lambda e: switch("Library"),
                      bgcolor=MINT, color=DARK),
            ft.Button("Back to insights", on_click=lambda e: switch("Stats"),
                      bgcolor=MINT, color=DARK),
        ]

    def render():
        sections = {
            "Home": home,
            "Scan": add_screen,
            "Receipt": receipt_scanner,
            "Library": receipt_library,
            "History": history,
            "Stats": stats,
            "Categories": categories,
        }

        controls = [
            ft.Row(controls=[
                txt("Receiptly", 26, DARK, True),
                ft.Container(expand=True),
                ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED, color=GREEN, size=28),
            ])
        ]

        if screen == "History":
            controls.append(ft.Row(controls=[
                ft.Container(expand=True),
                ft.Button("Remove all transactions", bgcolor="#C62828", color=WHITE,
                          disabled=not transactions, on_click=confirm_remove_all),
            ]))

        controls.extend(sections[screen]())

        nav = ft.Row(
            controls=[
                ft.Button(
                    label,
                    expand=True,
                    on_click=lambda e, x=destination: switch(x),
                    bgcolor=GREEN if screen == destination else WHITE,
                    color=WHITE if screen == destination else DARK,
                    style=ft.ButtonStyle(
                        padding=ft.Padding.symmetric(horizontal=2, vertical=9),
                        text_style=ft.TextStyle(size=11),
                    ),
                )
                for label, destination in (
                    ("Home", "Home"),
                    ("Scan", "Receipt"),
                    ("History", "History"),
                    ("Stats", "Stats"),
                )
            ],
            spacing=4,
            wrap=False,
            alignment=ft.MainAxisAlignment.CENTER,
        )

        # Only the main content scrolls; the navigation stays at the bottom.
        page.clean()
        page.scroll = None
        page.add(
            ft.SafeArea(
                expand=True,
                content=ft.Column(
                    expand=True,
                    spacing=0,
                    controls=[
                        ft.Column(
                            expand=True,
                            scroll=ft.ScrollMode.AUTO,
                            controls=[
                                ft.Container(
                                    content=ft.Column(
                                        controls=controls,
                                        spacing=16,
                                    ),
                                    padding=14,
                                )
                            ],
                        ),
                        ft.Container(
                            content=nav,
                            bgcolor=WHITE,
                            padding=ft.Padding.symmetric(
                                horizontal=8, vertical=7
                            ),
                        ),
                    ],
                ),
            )
        )
        page.update()

    await load_transactions()
    render()


if __name__ == "__main__":
    ft.run(main)
