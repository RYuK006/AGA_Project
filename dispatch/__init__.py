"""Dispatch module for Emergency Ambulance Routing System.
"""

from .dispatch_engine import dispatch_emergency_call, HospitalScore, DispatchResult

__all__ = ["dispatch_emergency_call", "HospitalScore", "DispatchResult"]
