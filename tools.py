import threading
import time
import uuid


# ==================================================
# TIMER MANAGER
# ==================================================

class TimerManager:

    def __init__(self):

        self.timers = {}

        self.lock = threading.Lock()


    # --------------------------------------------------
    # START TIMER
    # --------------------------------------------------

    def start_timer(
        self,
        seconds,
        purpose="cooking timer",
        step_id=None
    ):

        timer_id = str(uuid.uuid4())[:8]

        start_time = time.monotonic()

        timer_data = {
            "id": timer_id,
            "duration": seconds,
            "start_time": start_time,
            "purpose": purpose,
            "step_id": step_id,
            "status": "running",
            "finished": False
        }

        with self.lock:

            self.timers[timer_id] = timer_data


        thread = threading.Thread(
            target=self._run_timer,
            args=(timer_id,),
            daemon=True
        )

        thread.start()


        return {
            "timer_id": timer_id,
            "status": "running",
            "duration_seconds": seconds,
            "purpose": purpose,
            "step_id": step_id,
            "message": (
                f"Timer started for {seconds} seconds."
            )
        }


    # --------------------------------------------------
    # BACKGROUND TIMER
    # --------------------------------------------------

    def _run_timer(self, timer_id):

        with self.lock:

            timer = self.timers.get(timer_id)

            if timer is None:
                return

            seconds = timer["duration"]
            purpose = timer["purpose"]


        time.sleep(seconds)


        with self.lock:

            timer = self.timers.get(timer_id)

            if timer is None:
                return

            timer["status"] = "finished"
            timer["finished"] = True


        print("\n\n⏰ TIME'S UP!")

        print(
            f"Your {seconds}-second timer for "
            f"{purpose} is finished."
        )

        print(
            "You can continue chatting.\n"
        )


    # --------------------------------------------------
    # GET TIMER STATUS
    # --------------------------------------------------

    def get_status(self, timer_id=None):

        with self.lock:

            if not self.timers:

                return {
                    "status": "no_timer",
                    "message": "No timers exist."
                }


            if timer_id is None:

                timer = list(
                    self.timers.values()
                )[-1]

            else:

                timer = self.timers.get(
                    timer_id
                )

                if timer is None:

                    return {
                        "status": "not_found",
                        "message": "Timer not found."
                    }


            if timer["status"] == "finished":

                return {
                    "timer_id": timer["id"],
                    "status": "finished",
                    "remaining_seconds": 0,
                    "duration_seconds": timer["duration"],
                    "purpose": timer["purpose"],
                    "step_id": timer["step_id"]
                }


            elapsed = (
                time.monotonic()
                - timer["start_time"]
            )

            remaining = max(
                0,
                timer["duration"] - elapsed
            )


            return {
                "timer_id": timer["id"],
                "status": "running",
                "remaining_seconds": round(
                    remaining
                ),
                "duration_seconds": timer["duration"],
                "purpose": timer["purpose"],
                "step_id": timer["step_id"]
            }


    # --------------------------------------------------
    # ALL TIMER STATUS
    # --------------------------------------------------

    def get_all_status(self):

        with self.lock:

            result = []


            for timer in self.timers.values():

                if timer["status"] == "finished":

                    result.append({
                        "timer_id": timer["id"],
                        "status": "finished",
                        "remaining_seconds": 0,
                        "duration_seconds": timer["duration"],
                        "purpose": timer["purpose"],
                        "step_id": timer["step_id"]
                    })

                else:

                    elapsed = (
                        time.monotonic()
                        - timer["start_time"]
                    )

                    remaining = max(
                        0,
                        timer["duration"] - elapsed
                    )

                    result.append({
                        "timer_id": timer["id"],
                        "status": "running",
                        "remaining_seconds": round(
                            remaining
                        ),
                        "duration_seconds": timer["duration"],
                        "purpose": timer["purpose"],
                        "step_id": timer["step_id"]
                    })


            return result


# ==================================================
# GLOBAL TIMER MANAGER
# ==================================================

timer_manager = TimerManager()


# ==================================================
# TOOL FUNCTIONS
# ==================================================

def timer(
    seconds,
    purpose="cooking timer",
    step_id=None
):

    return timer_manager.start_timer(
        seconds,
        purpose,
        step_id
    )


def timer_status(timer_id=None):

    return timer_manager.get_status(
        timer_id
    )


# ==================================================
# TOOL REGISTRY
# ==================================================

TOOLS = {

    "timer": timer,

    "timer_status": timer_status

}