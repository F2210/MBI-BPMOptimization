"""
Healthcare Resource Optimization with Heuristic Planning

This module implements a heuristic-based planner for healthcare resource scheduling
and patient admission planning. It uses simulation to optimize resource allocation
across different time slots (morning, afternoon, evening, night) and different
resource types (OR, beds, intake, practitioners).

The planner aims to reduce waiting times, nervousness, and costs while maintaining
service quality in a healthcare setting.
"""

from math import floor
from simulator import Simulator
from planners import Planner
from problems import HealthcareProblem, ResourceType
from reporter import EventLogReporter, ResourceScheduleReporter
from resource_logistics import *
from enum import Enum
import os


class Weekday(Enum):
    """
    Enum representing days of the week, where Monday is 0 and Sunday is 6.
    Used for indexing weekly resource schedules and formatting day names.
    """

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

    def __str__(self):
        """Return capitalized day name (e.g., 'Monday' instead of 'MONDAY')"""
        return self.name.capitalize()


class HeuristicPlanner(Planner):
    """
    A heuristic-based planner for optimizing healthcare resource allocation and patient scheduling.

    This planner handles:
    - Patient admission planning based on resource availability
    - Resource scheduling for different time slots
    - Event reporting for simulation analysis
    - Tracking of resource utilization

    The planner uses a greedy approach to schedule patients while respecting constraints
    like advance notice requirements and resource availability.
    """

    def __init__(self, eventlog_file, data_columns, weekly_res_schedule):
        """
        Initialize the HeuristicPlanner with event logging and resource scheduling capabilities.

        Parameters:
            eventlog_file (str): Path to file where event logs will be stored
            data_columns (list): Additional data columns to track in event logs
            weekly_res_schedule (dict): Weekly schedule of resource availability
        """
        super().__init__()
        self.eventlog_reporter = EventLogReporter(eventlog_file, data_columns)
        self.resource_reporter = ResourceScheduleReporter()
        self.replanned_patients = (
            set()
        )  # Track patients whose appointments were rescheduled
        # Initialize availability tracker for intake resources (default: 4 intakers per hour)
        self.planned_intakers = [
            4
        ] * 10000  # List that tracks how many intakers are available per (simulation) hour
        self.not_planned_within_week_counter = (
            0  # Count cases that couldn't be scheduled within a week
        )
        self.weekly_resource_schedule = (
            weekly_res_schedule  # Store the weekly resource schedule
        )

    def update_intaker_schedule(self, scheduled_resources):
        """
        Adjusts the availability of the intakers based on the scheduled resources.

        Takes the scheduled resources and updates the internal intaker availability tracker
        to reflect when intakers are available throughout the day.

        Parameters:
            scheduled_resources (list): List of tuples in format (resource_type, time, count)
                Example: [('OR', 176, 4), ('A_BED', 176, 25), ('B_BED', 176, 35), ('INTAKE', 176, 4), ...]
        """
        # Only extract resources related to intake
        scheduled_intakes = [
            resource for resource in scheduled_resources if resource[0] == "INTAKE"
        ]

        # Update the availability for each time slot:
        # Morning (8-12): 4 hours
        for i in range(4):
            self.planned_intakers[scheduled_intakes[0][1] + i] = scheduled_intakes[0][2]
        # Afternoon (12-18): 6 hours
        for i in range(6):
            self.planned_intakers[scheduled_intakes[1][1] + i] = scheduled_intakes[1][2]
        # Evening (18-1): 7 hours
        for i in range(7):
            self.planned_intakers[scheduled_intakes[2][1] + i] = scheduled_intakes[2][2]
        # Night (1-8): 7 hours
        for i in range(7):
            self.planned_intakers[scheduled_intakes[3][1] + i] = scheduled_intakes[3][2]

    def report(self, case_id, element, timestamp, resource, lifecycle_state, data=None):
        """
        Record simulation events for later analysis and visualization.

        Each time a simulation event happens, this method is invoked to log the event
        to both the event log reporter and resource schedule reporter.

        Parameters:
            case_id (str): The case ID of the patient to which the event applies
            element (str): The process element (task or event) that started or completed
            timestamp (float): The simulation time at which the event happened
            resource (str): The resource that the patient is using (if any)
            lifecycle_state (str): The lifecycle state of the element ("start", "complete")
            data (dict, optional): Dictionary with additional data for the event
        """
        self.eventlog_reporter.callback(
            case_id, element, timestamp, resource, lifecycle_state
        )
        self.resource_reporter.callback(
            case_id, element, timestamp, resource, lifecycle_state, data
        )

    def plan(self, cases_to_plan, _, simulation_time):
        """
        Plan patient admissions based on intaker availability.

        Uses a greedy algorithm that assigns patients to the first available time slot
        with an available intaker, starting 24 hours ahead of the current simulation time.

        Parameters:
            cases_to_plan (list): List of case IDs that can be planned for admission
            cases_to_replan (list): List of case IDs that were already planned but can be rescheduled (We do not use this)
            simulation_time (float): The current simulation time

        Returns:
            list: List of tuples (case_id, admission_time) representing the planned admissions

        Constraints:
            - Patients must be planned for admission at least 24 hours ahead
        """
        planned_cases = []

        break_loops = False
        for case_id in cases_to_plan:
            i = 24  # Start looking 24 hours ahead (minimum required planning horizon)
            time_slot_found = False
            # Look for the first available INTAKE resource and plan the first case
            while not time_slot_found:
                # Check if an intaker is available at this time slot
                if self.planned_intakers[math.ceil(simulation_time) + i] > 0:
                    next_plannable_time = math.ceil(simulation_time) + i
                    planned_cases.append((case_id, next_plannable_time))
                    # Decrease the available intakers at this time slot
                    self.planned_intakers[floor(simulation_time) + i] -= 1
                    time_slot_found = True
                # If we've checked a week ahead and found no slots: plan this patient later, because we haven't scheduled the intakers yet.
                elif i > 168:  # 168 hours = 1 week
                    self.not_planned_within_week_counter += 1
                    # Break both the while loop and the for loop
                    break_loops = True
                    break

                i += 1  # Look at the next hour

            # If we couldn't find a slot within a week for one patient,
            # stop planning altogether to avoid excessive computation
            if break_loops:
                break

        # We don't replan already scheduled patients in this implementation
        # This could be extended to reschedule patients if needed

        return planned_cases

    def schedule(self, simulation_time):
        """
        Schedule healthcare resources for the following day and beyond.

        This method is called each day at 18:00 in simulation time to schedule
        resources for future time periods. It uses the weekly resource schedule
        defined for the planner to determine how many resources should be available
        in different time slots.

        Parameters:
            simulation_time (float): Current simulation time

        Returns:
            list: List of tuples (resource_type, start_time, count) representing scheduled resources

        Constraints:
            - Must schedule at least 14 hours ahead (for tomorrow's working day)
            - Cannot exceed maximum number of resources per type
            - For near-term scheduling (<158 hours), can only increase resource availability
        """
        # Calculate the current day of week and hour within the week
        hour_of_week = simulation_time % 168
        day_of_week = hour_of_week // 24  # Monday is 0, Tuesday is 1, ..., Sunday is 6

        # Set up the time slots for the next day, planning 7+ days ahead (182+ hours)
        # This exceeds the minimum requirement of 14 hours ahead
        start_morning = simulation_time + 182  # Starts at 8:00
        start_afternoon = simulation_time + 186  # Starts at 12:00
        start_evening = simulation_time + 192  # Starts at 18:00
        start_night = simulation_time + 199  # Starts at 01:00

        # Get the weekday name for resource scheduling
        week_day = str(Weekday(day_of_week))

        # Get the required resources for each time slot from the weekly schedule
        resources_next_morning = get_scheduled_resources(
            week_day, start_morning, self.weekly_resource_schedule
        )  # resources from 8-12
        resources_next_afternoon = get_scheduled_resources(
            week_day, start_afternoon, self.weekly_resource_schedule
        )  # resources from 12-18
        resources_next_evening = get_scheduled_resources(
            week_day, start_evening, self.weekly_resource_schedule
        )  # resources from 17-1
        resources_next_night = get_scheduled_resources(
            week_day, start_night, self.weekly_resource_schedule
        )  # resources from 1-8

        def format_resources():
            """
            Helper function to format resource schedules into the required tuple format.
            Converts dictionary representations to (resource_type, time, count) tuples.
            """
            # Convert each time slot's resources into tuples
            scheduled_resources_morning = [
                (resource_type, start_morning, value)
                for resource_type, value in resources_next_morning.items()
            ]
            scheduled_resources_afternoon = [
                (resource_type, start_afternoon, value)
                for resource_type, value in resources_next_afternoon.items()
            ]
            scheduled_resources_evening = [
                (resource_type, start_evening, value)
                for resource_type, value in resources_next_evening.items()
            ]
            scheduled_resources_night = [
                (resource_type, start_night, value)
                for resource_type, value in resources_next_night.items()
            ]
            # Combine all time slots into a single schedule
            return (
                scheduled_resources_morning
                + scheduled_resources_afternoon
                + scheduled_resources_evening
                + scheduled_resources_night
            )

        # Get the formatted resource schedule
        scheduled_resources = format_resources()

        # Update the intaker availability based on the new schedule
        self.update_intaker_schedule(scheduled_resources)

        return scheduled_resources


if __name__ == "__main__":
    """
    Main execution block that runs multiple simulations to evaluate the performance
    of the heuristic planner with a specific resource schedule.
    """

    # Use the first resource schedule from the predefined options
    optimized_resource_schedule = regular_resource_allocation[0]

    # Create the HeuristicPlanner and configure it with the optimized resource schedule
    planner = HeuristicPlanner(
        "./temp/event_log.csv", ["diagnosis"], optimized_resource_schedule
    )
    problem = HealthcareProblem()  # Initialize the healthcare problem definition
    simulator = Simulator(planner, problem)  # Set up the simulator

    # Run a year-long simulation (365 days * 24 hours)
    result = simulator.run(365 * 24)

    # Calculate the cost using the weighted formula:
    # - Waiting time for admission contributes to patient dissatisfaction
    # - Waiting time in hospital increases medical risks and costs
    # - Nervousness affects patient experience
    # - Personnel costs are multiplied by 3 to represent their significant impact on budget
    cost = (
        result["waiting_time_for_admission"]
        + result["waiting_time_in_hospital"]
        + result["nervousness"]
        + result["personnel_cost"] * 3
    )
    print(f"TOTAL COST = {cost}")

    # Save the simulation results to a file in the "runs" directory
    os.makedirs("runs", exist_ok=True)  # Create the runs directory if it doesn't exist
    i = len(os.listdir("runs")) + 1  # Get the next run number
    print(f"Saving run as run {i}...")
    with open(f"runs/run{i}.txt", "w") as file:
        file.write(f"Result: {result}\n")
        file.write(f"TOTAL COST = {cost}\n")

    # Generate visualization of resource usage from week 2 to week 8
    planner.resource_reporter.create_graph(168 * 2, 168 * 8)
