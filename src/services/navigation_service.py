from kivy.app import App


class NavigationService:
    def __init__(self):
        self.history = []

    def go_to(self, screen_name: str):
        app = App.get_running_app()

        if app.sm.current != screen_name:
            self.history.append(app.sm.current)
            app.sm.current = screen_name

    def go_back(self):
        app = App.get_running_app()

        if self.history:
            previous = self.history.pop()
            app.sm.current = previous
        else:
            app.sm.current = "menu"
