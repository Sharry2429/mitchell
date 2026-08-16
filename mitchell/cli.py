"""
mitchell.cli
The Mitchell Command Line Interface.
"""
import argparse
import sys
import logging
from mitchell.agents.orchestrator import Orchestrator

def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Mitchell Assistant CLI")
    parser.add_argument("task", nargs="+", help="Task to execute")
    
    args = parser.parse_args()
    task = " ".join(args.task)
    
    orchestrator = Orchestrator()
    print(f"Executing task: {task}")
    result = orchestrator.execute(task)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
