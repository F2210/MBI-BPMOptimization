"""
Resource Logistics Module

This module handles the logistics of resource allocation in a healthcare simulation environment.
It determines the number of resources (beds, practitioners, operating rooms, etc.) that should be
scheduled at different times of day, different days of the week, and on holidays.

The module uses time-based heuristics and historical data patterns to optimize resource allocation,
taking into account factors such as:
- Time of day (divided into four time slots)
- Day of week
- Holiday status
- Resource type-specific constraints and requirements
"""

import math
import numpy as np
from dutch_holidays import check_if_holiday


def get_time_slot(hour_in_simulation: int) -> str:
    """
    Determine the time slot category based on the hour in simulation.

    The day is divided into four time slots to reflect different operational patterns:
    - "01-08": Night shift/early morning (1am to 8am)
    - "08-12": Morning shift (8am to 12pm)
    - "12-18": Afternoon/early evening shift (12pm to 6pm)
    - "18-01": Evening/night shift (6pm to 1am)

    Parameters:
        hour_in_simulation (int): Current hour in the simulation (can be >24)

    Returns:
        str: Time slot identifier ("01-08", "08-12", "12-18", or "18-01")
    """
    # Convert simulation hours to hour of the day (0-23)
    hour_in_day = hour_in_simulation % 24

    # Determine time slot based on hour of day
    if hour_in_day >= 1 and hour_in_day < 8:
        return "01-08"
    elif hour_in_day >= 8 and hour_in_day < 12:
        return "08-12"
    elif hour_in_day >= 12 and hour_in_day < 18:
        return "12-18"
    else:
        # This covers both 0 and 18-23 hours (6pm to 1am)
        return "18-01"


def get_scheduled_resources(day_of_week: str, hour: int, regular_resource_allocation):
    """
    Calculate the number of resources to schedule based on time, day, and holiday status.

    This function determines optimal resource allocation by:
    1. Identifying the appropriate time slot for the given hour
    2. Retrieving base resource values for that day and time slot
    3. Adjusting for holidays by reducing certain resources
    4. Enforcing maximum capacity constraints for each resource type

    Parameters:
        day_of_week (str): Day of the week (e.g., "Monday", "Tuesday")
        hour (int): Current hour in simulation
        regular_resource_allocation (dict): Dictionary containing base resource allocation values
                                  by day and time slot

    Returns:
        dict: Scheduled resource counts for each resource type

    Notes:
        Resource types include:
        - OR: Operating Rooms (max 5)
        - A_BED: Type A Beds (max 30)
        - B_BED: Type B Beds (max 40)
        - INTAKE: Intake capacity (max 4)
        - ER_PRACTITIONER: Emergency practitioners (max 9)
    """
    # 1. Get the time slot of the hour that we will have to schedule.
    time_slot = get_time_slot(hour)

    # 2. Get the corresponding values for number of resources from the resource_allocation dictionary
    regular_resource_allocation = regular_resource_allocation[day_of_week][time_slot]

    # 3. Check if the current hour falls on a holiday to adjust resource allocation
    isHoliday = check_if_holiday(hour)

    # 4. Put resources in the scheduled dictionary and take into account the maximum capacity limits
    # Each resource type has specific handling logic and capacity constraints
    scheduled = {}
    for resource_type, amount in regular_resource_allocation.items():
        if resource_type == "OR":
            # Operating rooms are reduced by 50% on holidays, with minimum of 1
            if isHoliday:
                amount = max(1, int(math.ceil(amount * 0.5)))
            # Enforce maximum capacity of 5 ORs
            scheduled[resource_type] = min(amount, 5)
        elif resource_type == "A_BED":
            # A-type beds are reduced by 20% on holidays
            if isHoliday:
                amount = int(round(amount * 0.8))
            # Enforce maximum capacity of 30 A-type beds
            scheduled[resource_type] = min(amount, 30)
        elif resource_type == "B_BED":
            # B-type beds are reduced by 20% on holidays
            if isHoliday:
                amount = int(round(amount * 0.8))
            # Enforce maximum capacity of 40 B-type beds
            scheduled[resource_type] = min(amount, 40)
        elif resource_type == "INTAKE":
            # On holidays, only 1 intake resource is scheduled
            if isHoliday:
                amount = 1
            # Enforce maximum capacity of 4 intake resources
            scheduled[resource_type] = min(amount, 4)
        else:
            # Raise error for unknown resource types to prevent silent failures
            raise ValueError(
                "An unknown resource type has been given in get_scheduled_resources in resource_logistics.py"
            )

    # ER practitioners are calculated separately due to more complex scheduling patterns
    scheduled["ER_PRACTITIONER"] = get_er_practitioner_amount(hour, isHoliday)

    return scheduled


def get_er_practitioner_amount(hour, isHoliday):
    """
    Calculate the optimal number of ER practitioners based on time of day and holiday status.

    ER practitioner scheduling is more complex and follows these principles:
    - Evening hours (18-23:59) see exponential increase in demand
    - Early morning hours (0-2:30) need higher staffing to handle overnight cases
    - Holiday status significantly increases the required staff
    - Minimum of 2 practitioners are always scheduled

    Parameters:
        hour (int): Current hour in simulation
        isHoliday (bool): Whether the current day is a holiday

    Returns:
        int: Number of ER practitioners to schedule (between 2 and 9)
    """
    # Convert simulation hour to hour within the current day (0-23)
    hour_of_day = hour % 24

    # In the evening, there are many emergency patients, exponentially increasing until 23h
    if hour_of_day >= 18 and hour_of_day <= 23.999:
        if isHoliday:
            # Holidays have significantly higher ER demand in evenings
            # Formula derived from historical data analysis in Excel
            amount = 0.9243 * np.exp(0.3888 * hour_of_day) * 2
        else:
            # Regular evenings still see exponential increase but less steep
            amount = 0.8879 * np.exp(0.2757 * hour_of_day) * 2
    elif hour_of_day >= 0 and hour_of_day <= 2.5:
        if isHoliday:
            # Early morning hours after holiday nights are peak demand
            amount = 9  # Maximum capacity
        else:
            # Regular early mornings still need high staff due to overnight cases
            # and because average ER treatment takes ~2 hours
            amount = 5
    else:
        # Other hours have more stable, lower demand
        if isHoliday:
            amount = 4  # Moderate staffing for daytime holidays
        else:
            amount = 2  # Minimum staffing for regular daytime hours

    # Ensure ER practitioner count is always between minimum (2) and maximum (9)
    # Round to nearest integer since we can't have partial practitioners
    amount = max(2, int(round(amount)))
    return min(amount, 9)


# Resource estimates for different days and time slots
# These values represent the baseline resource requirements before
# adjustments for holidays and capacity constraints
regular_resource_allocation = [
    {  # model based on average resource usage from historical data
        "Monday": {
            "08-12": {"A_BED": 17, "B_BED": 40, "INTAKE": 4, "OR": 2},
            "12-18": {"A_BED": 21, "B_BED": 39, "INTAKE": 4, "OR": 5},
            "18-01": {"A_BED": 24, "B_BED": 40, "INTAKE": 2, "OR": 3},
            "01-08": {"A_BED": 21, "B_BED": 39, "INTAKE": 2, "OR": 2},
        },
        "Tuesday": {
            "08-12": {"A_BED": 23, "B_BED": 40, "INTAKE": 4, "OR": 2},
            "12-18": {"A_BED": 25, "B_BED": 40, "INTAKE": 4, "OR": 5},
            "18-01": {"A_BED": 26, "B_BED": 40, "INTAKE": 3, "OR": 3},
            "01-08": {"A_BED": 25, "B_BED": 39, "INTAKE": 4, "OR": 2},
        },
        "Wednesday": {
            "08-12": {"A_BED": 27, "B_BED": 40, "INTAKE": 4, "OR": 2},
            "12-18": {"A_BED": 27, "B_BED": 40, "INTAKE": 4, "OR": 5},
            "18-01": {"A_BED": 26, "B_BED": 40, "INTAKE": 2, "OR": 3},
            "01-08": {"A_BED": 27, "B_BED": 40, "INTAKE": 4, "OR": 2},
        },
        "Thursday": {
            "08-12": {"A_BED": 27, "B_BED": 40, "INTAKE": 4, "OR": 2},
            "12-18": {"A_BED": 27, "B_BED": 40, "INTAKE": 4, "OR": 5},
            "18-01": {"A_BED": 26, "B_BED": 40, "INTAKE": 2, "OR": 4},
            "01-08": {"A_BED": 26, "B_BED": 40, "INTAKE": 4, "OR": 2},
        },
        "Friday": {
            "08-12": {"A_BED": 26, "B_BED": 40, "INTAKE": 4, "OR": 2},
            "12-18": {"A_BED": 23, "B_BED": 40, "INTAKE": 1, "OR": 1},
            "18-01": {"A_BED": 21, "B_BED": 40, "INTAKE": 1, "OR": 1},
            "01-08": {"A_BED": 27, "B_BED": 40, "INTAKE": 4, "OR": 2},
        },
        "Saturday": {
            "08-12": {"A_BED": 16, "B_BED": 40, "OR": 1, "INTAKE": 4},
            "12-18": {"A_BED": 13, "B_BED": 40, "OR": 1, "INTAKE": 4},
            "18-01": {"A_BED": 13, "B_BED": 40, "OR": 1, "INTAKE": 2},
            "01-08": {"A_BED": 20, "B_BED": 40, "OR": 2, "INTAKE": 2},
        },
        "Sunday": {
            "08-12": {"A_BED": 9, "B_BED": 40, "INTAKE": 4, "OR": 2},
            "12-18": {"A_BED": 14, "B_BED": 39, "INTAKE": 4, "OR": 5},
            "18-01": {"A_BED": 18, "B_BED": 40, "INTAKE": 2, "OR": 3},
            "01-08": {"A_BED": 13, "B_BED": 40, "INTAKE": 2, "OR": 2},
        },
    }
]
