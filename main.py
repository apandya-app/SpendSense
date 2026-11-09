
import flet as ft

def main(page: ft.Page):
    page.title = "SpendSense"
    page.bgcolor = "#F5FAF6"
    page.padding = 25

    page.add(
        ft.Text(
            "SpendSense",
            size=32,
            weight=ft.FontWeight.BOLD,
            color="#14362B",
        ),
        ft.Text(
            "Snap. Track. Save.",
            size=17,
            color="#207B51",
        ),
        ft.Divider(),
        ft.Text(
            "Welcome to SpendSense!",
            size=22,
            color="#14362B",
        ),
        ft.Button("Scan your receipt"),
        ft.Text(
            "Your spending dashboard is coming soon.",
            color="#207B51",
        ),
    )

ft.run(main)
