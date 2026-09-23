import asyncio
import json
import os
import toga
from toga.style import Pack
from toga.style.pack import ROW, COLUMN, CENTER, BOLD

DATA_FILE = "long_term_goals.json"
MAX_SESSION_MINS = 120  # Maximum macro focus session limit in minutes

class MiniTimerApp(toga.App):
    def startup(self):
        # Data & State Variables
        self.long_term_goals = self.load_goals()
        self.active_lt_goal_id = None
        
        self.yes_count = 0
        self.no_count = 0
        
        # Macro focus session variables
        self.macro_total_seconds = 0
        self.macro_remaining_seconds = 0
        
        # Micro mini-session variables
        self.mini_total_seconds = 0
        self.mini_remaining_seconds = 0
        self.phase_timer_seconds = 0
        self.current_goal_text = ""
        
        # States: 'IDLE', 'PLANNING', 'MINI_RUNNING', 'REVIEW'
        self.state = 'IDLE'
        self.timer_task = None

        # Main Layout Box
        main_box = toga.Box(style=Pack(direction=ROW, margin=10))

        # ==========================================
        # LEFT PANEL: MiniTimer Engine
        # ==========================================
        left_box = toga.Box(style=Pack(direction=COLUMN, flex=1, margin=10))

        # Macro Session Overview Header
        self.macro_timer_label = toga.Label(
            "Macro Focus Session: Idle",
            style=Pack(font_size=14, font_weight=BOLD, text_align=CENTER, margin_bottom=5)
        )

        # Cosmetic Session Title Input
        title_row = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))
        title_row.add(toga.Label("Session Title: ", style=Pack(width=140)))
        self.session_title_input = toga.TextInput(placeholder="Cosmetic session title...", style=Pack(flex=1))
        title_row.add(self.session_title_input)

        # Top Display: Large Active Goal & Large Micro Timer Countdown
        self.goal_display_label = toga.Label(
            "Set a focus limit & start session",
            style=Pack(font_size=20, font_weight=BOLD, text_align=CENTER, margin_bottom=5)
        )
        self.timer_label = toga.Label(
            "00:00",
            style=Pack(font_size=36, font_weight=BOLD, text_align=CENTER, margin_bottom=5)
        )
        self.prompt_status_label = toga.Label(
            "Ready to start macro session.",
            style=Pack(text_align=CENTER, font_size=12, margin_bottom=10)
        )

        # Macro Controls Box (Configuring overall focus limit)
        macro_controls_box = toga.Box(style=Pack(direction=ROW, margin_bottom=10, align_items=CENTER))
        macro_controls_box.add(toga.Label("Focus Limit (mins): ", style=Pack(width=140)))
        self.macro_limit_input = toga.NumberInput(
            value=25,
            min=1,
            max=MAX_SESSION_MINS,
            style=Pack(flex=1)
        )
        macro_controls_box.add(self.macro_limit_input)

        self.start_macro_btn = toga.Button("Start Focus Session", on_press=self.on_start_macro_pressed, style=Pack(margin_bottom=10))

        # Micro Controls Box (Configuring immediate mini-goal and duration 40-120s)
        micro_controls_box = toga.Box(style=Pack(direction=COLUMN, margin_bottom=10))
        
        goal_row = toga.Box(style=Pack(direction=ROW, margin_bottom=5, align_items=CENTER))
        goal_row.add(toga.Label("Mini Goal: ", style=Pack(width=140)))
        self.mini_goal_input = toga.TextInput(placeholder="Enter micro-goal text...", style=Pack(flex=1))
        self.mini_goal_input.enabled = False
        goal_row.add(self.mini_goal_input)

        duration_row = toga.Box(style=Pack(direction=ROW, margin_bottom=5, align_items=CENTER))
        duration_row.add(toga.Label("Duration (40-120s): ", style=Pack(width=140)))
        self.mini_duration_input = toga.NumberInput(
            value=40,
            min=40,
            max=120,
            style=Pack(flex=1)
        )
        self.mini_duration_input.enabled = False
        duration_row.add(self.mini_duration_input)

        micro_controls_box.add(goal_row)
        micro_controls_box.add(duration_row)

        mini_btn_box = toga.Box(style=Pack(direction=ROW, margin_bottom=5))
        self.start_mini_btn = toga.Button("Start Mini-Session", on_press=self.on_start_mini_pressed, style=Pack(flex=1, margin_right=5))
        self.start_mini_btn.enabled = False

        self.end_mini_early_btn = toga.Button("End Mini Early", on_press=self.on_end_mini_early_pressed, style=Pack(flex=1))
        self.end_mini_early_btn.enabled = False

        mini_btn_box.add(self.start_mini_btn)
        mini_btn_box.add(self.end_mini_early_btn)

        # Prompt Action Buttons (Met / Not Met during Review Phase)
        self.met_btn = toga.Button("Met", on_press=self.on_met_pressed, style=Pack(flex=1, margin_right=5))
        self.met_btn.enabled = False
        
        self.not_met_btn = toga.Button("Not Met", on_press=self.on_not_met_pressed, style=Pack(flex=1))
        self.not_met_btn.enabled = False
        
        review_btn_box = toga.Box(style=Pack(direction=ROW, margin_bottom=10))
        review_btn_box.add(self.met_btn)
        review_btn_box.add(self.not_met_btn)

        # Yes / No Pile Bar Visualization
        pile_label = toga.Label("Session Results Bar (Green / Red):", style=Pack(margin_top=10, margin_bottom=5))
        
        bar_container = toga.Box(style=Pack(direction=ROW, height=30, margin_bottom=10))
        self.green_bar = toga.Box(style=Pack(background_color='green', flex=1))
        self.red_bar = toga.Box(style=Pack(background_color='red', flex=1))
        bar_container.add(self.green_bar)
        bar_container.add(self.red_bar)

        self.pile_stats_label = toga.Label("Yes: 0 | No: 0", style=Pack(text_align=CENTER))

        # Pack Left Panel Elements
        left_box.add(self.macro_timer_label)
        left_box.add(title_row)
        left_box.add(self.goal_display_label)
        left_box.add(self.timer_label)
        left_box.add(self.prompt_status_label)
        left_box.add(macro_controls_box)
        left_box.add(self.start_macro_btn)
        left_box.add(micro_controls_box)
        left_box.add(mini_btn_box)
        left_box.add(review_btn_box)
        left_box.add(pile_label)
        left_box.add(bar_container)
        left_box.add(self.pile_stats_label)

        # ==========================================
        # RIGHT PANEL: Long-Term Goals Panel
        # ==========================================
        right_box = toga.Box(style=Pack(direction=COLUMN, flex=1, margin=10))
        right_box.add(toga.Label("Long-Term Goals (Sorted by Deadline)", style=Pack(font_weight=BOLD, margin_bottom=10)))

        # Goals Table
        self.lt_table = toga.Table(
            columns=["Active", "Goal", "Deadline", "Done", "Green %", "Red %"],
            data=[],
            style=Pack(flex=1, margin_bottom=10)
        )
        self.update_table_data()

        # Add Long Term Goal Controls
        lt_input_box = toga.Box(style=Pack(direction=COLUMN, margin_bottom=5))
        self.lt_title_input = toga.TextInput(placeholder="Goal Description", style=Pack(margin_bottom=2))
        self.lt_date_input = toga.TextInput(placeholder="Deadline (YYYY-MM-DD)", style=Pack(margin_bottom=5))
        
        lt_input_box.add(self.lt_title_input)
        lt_input_box.add(self.lt_date_input)

        lt_btn_box = toga.Box(style=Pack(direction=ROW))
        add_lt_btn = toga.Button("Add Goal", on_press=self.add_lt_goal, style=Pack(flex=1, margin_right=2))
        toggle_done_btn = toga.Button("Toggle Done", on_press=self.toggle_lt_done, style=Pack(flex=1, margin_right=2))
        make_active_btn = toga.Button("Set Active", on_press=self.set_active_lt_goal, style=Pack(flex=1, margin_right=2))
        remove_lt_btn = toga.Button("Remove", on_press=self.remove_lt_goal, style=Pack(flex=1))

        lt_btn_box.add(add_lt_btn)
        lt_btn_box.add(toggle_done_btn)
        lt_btn_box.add(make_active_btn)
        lt_btn_box.add(remove_lt_btn)

        right_box.add(self.lt_table)
        right_box.add(lt_input_box)
        right_box.add(lt_btn_box)

        # Build Main Layout
        main_box.add(left_box)
        main_box.add(right_box)

        self.main_window = toga.MainWindow(title=self.formal_name, size=(950, 600))
        self.main_window.content = main_box
        self.main_window.on_close = self.confirm_window_close
        self.main_window.show()

        # Initialize UI state
        self.update_bars()

    # ==========================================
    # ASYNC TIMER ENGINE & STATE MACHINE
    # ==========================================
    async def run_timer_loop(self, app):
        """Main async background loop handling macro and micro timer ticks."""
        while self.state != 'IDLE':
            await asyncio.sleep(1.0)

            # 1. Tick Macro Timer
            if self.macro_remaining_seconds > 0:
                self.macro_remaining_seconds -= 1
                mm, ms = divmod(self.macro_remaining_seconds, 60)
                stitle = f" [{self.session_title_input.value}]" if self.session_title_input.value else ""
                self.macro_timer_label.text = f"Macro Focus Session{stitle}: {mm:02d}:{ms:02d} Remaining"
            else:
                self.prompt_status_label.text = "Macro focus session complete!"
                self.reset_to_idle()
                break

            # 2. State Machine for Micro Mini-Sessions
            if self.state == 'PLANNING':
                if self.phase_timer_seconds > 0:
                    self.phase_timer_seconds -= 1
                    self.timer_label.text = f"00:{self.phase_timer_seconds:02d}"
                    self.prompt_status_label.text = f"25s Planning Window: Enter goal & start ({self.phase_timer_seconds}s left)"
                else:
                    self.no_count += 1
                    self.update_bars()
                    self.prompt_status_label.text = "Planning timeout! Added flag to NO pile. Restarting 25s window..."
                    self.enter_planning_phase()

            elif self.state == 'MINI_RUNNING':
                if self.mini_remaining_seconds > 0:
                    self.mini_remaining_seconds -= 1
                    m, s = divmod(self.mini_remaining_seconds, 60)
                    self.timer_label.text = f"{m:02d}:{s:02d}"
                    self.prompt_status_label.text = f"Focusing on Mini Goal..."
                else:
                    self.enter_review_phase()

            elif self.state == 'REVIEW':
                if self.phase_timer_seconds > 0:
                    self.phase_timer_seconds -= 1
                    self.timer_label.text = f"00:{self.phase_timer_seconds:02d}"
                    self.prompt_status_label.text = f"Goal Finished! Click Met or Not Met ({self.phase_timer_seconds}s left)"
                else:
                    self.no_count += 1
                    self.update_bars()
                    self.prompt_status_label.text = "Review timeout! Added flag to NO pile."
                    self.enter_planning_phase()

    def on_start_macro_pressed(self, widget):
        try:
            mins = float(self.macro_limit_input.value)
        except (ValueError, TypeError):
            mins = 25

        if mins > MAX_SESSION_MINS:
            self.main_window.info_dialog("Limit Exceeded", f"Maximum focus session limit is {MAX_SESSION_MINS} minutes.")
            self.macro_limit_input.value = MAX_SESSION_MINS
            mins = MAX_SESSION_MINS

        self.macro_total_seconds = int(mins * 60)
        self.macro_remaining_seconds = self.macro_total_seconds
        
        # Reset session counts
        self.yes_count = 0
        self.no_count = 0
        self.update_bars()

        # Lock macro start controls
        self.start_macro_btn.enabled = False
        self.macro_limit_input.enabled = False
        self.session_title_input.enabled = False

        # Enter first mini-session planning phase
        self.enter_planning_phase()

        # Start background timer
        if self.timer_task:
            self.timer_task.cancel()
        self.timer_task = asyncio.create_task(self.run_timer_loop(self))

    def enter_planning_phase(self):
        self.state = 'PLANNING'
        self.phase_timer_seconds = 25
        self.mini_total_seconds = 0
        self.mini_remaining_seconds = 0
        self.timer_label.text = "00:25"
        self.prompt_status_label.text = "25s Planning Window: Enter goal & start"

        # Enable micro goal inputs
        self.mini_goal_input.enabled = True
        self.mini_duration_input.enabled = True
        self.start_mini_btn.enabled = True
        self.end_mini_early_btn.enabled = False
        self.met_btn.enabled = False
        self.not_met_btn.enabled = False

    def on_start_mini_pressed(self, widget):
        goal_text = self.mini_goal_input.value.strip() if self.mini_goal_input.value else ""
        if not goal_text:
            self.main_window.info_dialog("Goal Required", "Please enter a micro-goal before starting the mini-session.")
            return

        try:
            dur = int(self.mini_duration_input.value)
        except (ValueError, TypeError):
            dur = 40

        dur = max(40, min(120, dur))
        self.mini_duration_input.value = dur

        self.current_goal_text = goal_text
        self.goal_display_label.text = self.current_goal_text
        self.mini_total_seconds = dur
        self.mini_remaining_seconds = dur

        # Lock micro goal inputs during run & enable 'End Mini Early'
        self.mini_goal_input.enabled = False
        self.mini_duration_input.enabled = False
        self.start_mini_btn.enabled = False
        self.end_mini_early_btn.enabled = True

        self.state = 'MINI_RUNNING'

    def on_end_mini_early_pressed(self, widget):
        """Ends ONLY the active mini-session early while keeping macro session active."""
        if self.state == 'MINI_RUNNING':
            half_time = self.mini_total_seconds / 2.0
            if self.mini_remaining_seconds > half_time:
                self.yes_count += 2
                self.update_bars()
                self.prompt_status_label.text = "Mini ended before half-time! 2 Green Credits awarded."
            else:
                self.prompt_status_label.text = "Mini ended early."

            self.end_mini_early_btn.enabled = False
            self.enter_review_phase()

    def enter_review_phase(self):
        self.state = 'REVIEW'
        self.phase_timer_seconds = 25
        self.timer_label.text = "00:25"
        self.prompt_status_label.text = "Goal Finished! Click Met or Not Met"

        # Enable review buttons and allow typing new goal for 'Not Met' case
        self.met_btn.enabled = True
        self.not_met_btn.enabled = True
        self.end_mini_early_btn.enabled = False
        self.mini_goal_input.enabled = True
        self.mini_duration_input.enabled = True

    def on_met_pressed(self, widget):
        if self.state == 'REVIEW':
            self.yes_count += 1
            self.update_bars()
            self.prompt_status_label.text = "Goal Met! Added flag to YES pile."
            self.enter_planning_phase()

    def on_not_met_pressed(self, widget):
        if self.state == 'REVIEW':
            goal_text = self.mini_goal_input.value.strip() if self.mini_goal_input.value else ""
            if not goal_text:
                self.main_window.info_dialog("Goal Required", "Please type a new extension goal/timeframe for 'Not Met'.")
                return

            try:
                dur = int(self.mini_duration_input.value)
            except (ValueError, TypeError):
                dur = 40

            dur = max(40, min(120, dur))

            # Add flag to NO pile
            self.no_count += 1
            self.update_bars()

            # Start extension mini-session immediately
            self.current_goal_text = goal_text
            self.goal_display_label.text = f"[EXT] {self.current_goal_text}"
            self.mini_total_seconds = dur
            self.mini_remaining_seconds = dur

            self.mini_goal_input.enabled = False
            self.mini_duration_input.enabled = False
            self.met_btn.enabled = False
            self.not_met_btn.enabled = False
            self.end_mini_early_btn.enabled = True

            self.state = 'MINI_RUNNING'

    def reset_to_idle(self):
        self.state = 'IDLE'
        if self.timer_task:
            self.timer_task.cancel()
            self.timer_task = None

        self.start_macro_btn.enabled = True
        self.macro_limit_input.enabled = True
        self.session_title_input.enabled = True
        
        self.mini_goal_input.enabled = False
        self.mini_duration_input.enabled = False
        self.start_mini_btn.enabled = False
        self.end_mini_early_btn.enabled = False
        self.met_btn.enabled = False
        self.not_met_btn.enabled = False

        self.macro_timer_label.text = "Macro Focus Session: Idle"
        self.timer_label.text = "00:00"
        self.goal_display_label.text = "Session Complete"

        # Sync results to Active Long-Term Goal
        self.sync_session_to_lt_goal()

    def update_bars(self):
        total = self.yes_count + self.no_count
        if total == 0:
            self.green_bar.style.flex = 1
            self.red_bar.style.flex = 1
        else:
            self.green_bar.style.flex = max(self.yes_count, 1)
            self.red_bar.style.flex = max(self.no_count, 1)

        self.pile_stats_label.text = f"Yes: {self.yes_count}  |  No: {self.no_count}"
        
        if hasattr(self, 'green_bar') and self.green_bar.parent:
            self.green_bar.parent.refresh()

    async def confirm_window_close(self, window):
        """Intercept window close request requiring triple-confirmation during active sessions."""
        if self.state == 'IDLE':
            return True

        c1 = await window.confirm_dialog("Confirmation 1/3", "A focus session is running. Are you sure you want to exit?")
        if not c1:
            return False

        c2 = await window.confirm_dialog("Confirmation 2/3", "Exiting now will abandon current session stats. Continue exit?")
        if not c2:
            return False

        c3 = await window.confirm_dialog("Confirmation 3/3", "Final Confirmation: Really quit and close the application?")
        return c3

    # ==========================================
    # DISK STORAGE & LONG TERM GOALS
    # ==========================================
    def load_goals(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_goals(self):
        with open(DATA_FILE, 'w') as f:
            json.dump(self.long_term_goals, f, indent=2)

    def update_table_data(self):
        # Sort long-term goals by deadline date
        self.long_term_goals.sort(key=lambda x: x.get('deadline', '9999-99-99'))
        
        table_rows = []
        for g in self.long_term_goals:
            active_marker = "★ Active" if g.get('id') == self.active_lt_goal_id else ""
            done_marker = "Yes" if g.get('done') else "No"
            green_pct = f"{g.get('green_pct', 0.0):.1f}%"
            red_pct = f"{g.get('red_pct', 0.0):.1f}%"
            
            table_rows.append((
                active_marker,
                g.get('title', ''),
                g.get('deadline', ''),
                done_marker,
                green_pct,
                red_pct
            ))
        
        self.lt_table.data = table_rows

    def add_lt_goal(self, widget):
        title = self.lt_title_input.value.strip() if self.lt_title_input.value else ""
        deadline = self.lt_date_input.value.strip() if self.lt_date_input.value else ""

        if not title:
            self.main_window.info_dialog("Invalid Input", "Goal description is required.")
            return

        new_id = len(self.long_term_goals) + 1
        self.long_term_goals.append({
            "id": new_id,
            "title": title,
            "deadline": deadline if deadline else "9999-12-31",
            "done": False,
            "green_pct": 0.0,
            "red_pct": 0.0,
            "sessions_count": 0
        })

        self.save_goals()
        self.update_table_data()
        self.lt_title_input.value = ""
        self.lt_date_input.value = ""

    def toggle_lt_done(self, widget):
        selection = self.lt_table.selection
        if selection is None:
            return
        
        idx = self.get_selected_goal_index(selection)
        if idx is not None:
            self.long_term_goals[idx]['done'] = not self.long_term_goals[idx]['done']
            self.save_goals()
            self.update_table_data()

    def set_active_lt_goal(self, widget):
        selection = self.lt_table.selection
        if selection is None:
            return
        
        idx = self.get_selected_goal_index(selection)
        if idx is not None:
            self.active_lt_goal_id = self.long_term_goals[idx]['id']
            self.mini_goal_input.value = self.long_term_goals[idx]['title']
            self.update_table_data()

    def remove_lt_goal(self, widget):
        selection = self.lt_table.selection
        if selection is None:
            return
        
        idx = self.get_selected_goal_index(selection)
        if idx is not None:
            if self.long_term_goals[idx]['id'] == self.active_lt_goal_id:
                self.active_lt_goal_id = None
            del self.long_term_goals[idx]
            self.save_goals()
            self.update_table_data()

    def get_selected_goal_index(self, selection):
        selected_title = selection.goal
        selected_deadline = selection.deadline
        for i, g in enumerate(self.long_term_goals):
            if g['title'] == selected_title and g['deadline'] == selected_deadline:
                return i
        return None

    def sync_session_to_lt_goal(self):
        if not self.active_lt_goal_id:
            return

        total = self.yes_count + self.no_count
        if total == 0:
            return

        session_green_pct = (self.yes_count / total) * 100.0
        session_red_pct = (self.no_count / total) * 100.0

        for g in self.long_term_goals:
            if g['id'] == self.active_lt_goal_id:
                prev_count = g.get('sessions_count', 0)
                g['green_pct'] = ((g.get('green_pct', 0.0) * prev_count) + session_green_pct) / (prev_count + 1)
                g['red_pct'] = ((g.get('red_pct', 0.0) * prev_count) + session_red_pct) / (prev_count + 1)
                g['sessions_count'] = prev_count + 1
                break

        self.save_goals()
        self.update_table_data()

def main():
    return MiniTimerApp("MiniTimer", "org.beeware.minitimer")

if __name__ == "__main__":
    main().main_loop()