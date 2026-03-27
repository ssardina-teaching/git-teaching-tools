"""
Build the section for the classroom-resources/autograding-grading-reporter@v1 runner:
https://github.com/classroom-resources/autograding-grading-reporter

    - name: Autograding Reporter
      uses: classroom-resources/autograding-grading-reporter@v1
      env:
        LIVE_RESULTS: "${{steps.live.outputs.result}}"
        MESSI_RESULTS: "${{steps.messi.outputs.result}}"
        MAP-SOUND_RESULTS: "${{steps.map-sound.outputs.result}}"
        MAP-OPTIMAL_RESULTS: "${{steps.map-optimal.outputs.result}}"
      with:
        runners: live,messi,map-sound,map-optimal

❯ python ../../tools/git-hw-submissions.git/ghc_build_reporter.py workshop-4-ssardina.git/.github/workflows/classroom.yml
"""
__author__ = "Sebastian Sardina - ssardina - ssardina@gmail.com"
__copyright__ = "Copyright 2025"
import csv
import os
from argparse import ArgumentParser
import time
import util, utils_gh
import yaml


if __name__ == "__main__":
    parser = ArgumentParser(description="Produce GH Classroom automarking reporter section")
    parser.add_argument(
        "YAML",
        type=str,
        help="File with the automarking YAML workflow file.",
    )
    args = parser.parse_args()

    # Read the YAML file
    with open(args.YAML, 'r') as yaml_file:
        try:
            yaml_content = yaml.safe_load(yaml_file)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file: {e}")
            exit(1)

    steps = yaml_content["jobs"]["run-autograding-tests"]['steps']
    
    questions =  [(s["name"], s["with"]["max-score"]) for s in steps if "uses" in s and "classroom-resources/autograding-command-grader" in s["uses"]]
    
    envs_tests = ""
    runners = ""
    marks =0 
    for q in questions:
        envs_tests += "\n" + f"\t{q[0].upper()}_RESULTS: ${{{{steps.{q[0]}.outputs.result}}}}"
        marks += q[1]
    runners += ",".join([q[0] for q in questions])    
    
    
    print("Total marks: ", marks)
    
    output = rf"""
- name: Autograding Reporter
  uses: classroom-resources/autograding-grading-reporter@v1
  env: {envs_tests}
  with:
    runners: {runners}
"""
        
    print(output)
