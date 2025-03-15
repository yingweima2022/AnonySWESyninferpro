import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import argparse
import json

from datasets import load_dataset

from app.api.run_tests import run_reproduction_tests, txt_file_contains_string

execution_results = dict()


def load_jsonl(filepath):
    """
    Load a JSONL file from the given filepath.

    Arguments:
    filepath -- the path to the JSONL file to load

    Returns:
    A list of dictionaries representing the data in each line of the JSONL file.
    """
    with open(filepath, "r") as file:
        return [json.loads(line) for line in file]


def run_reproduction_for_each_instance(args, lines, run_id, test_jsonl, remove_docker_image):
    instance_ids = [line["instance_id"] for line in lines]
    patches = [line["model_patch"] for line in lines]

    results = run_reproduction_tests(
        instance_ids,
        patches,
        args.num_workers,
        run_id,
        args.instance_ids,
        args.timeout,
        testing_patches=False,
        apply_model_patch=True,
        remove_docker_image=remove_docker_image,
        test_jsonl=test_jsonl,
        dataset_name=args.dataset,
    )
    return results


def _run_reproduction_tests(args):
    if args.testing:
        # for reproduction test selection
        # run on original repo to select tests which can reproduce the issue
        ds = load_dataset(args.dataset)
        instance_ids = ds["test"]["instance_id"]
        patches = [
            {"instance_id": instance_id, "patch": "", "normalized_patch": ""}
            for instance_id in instance_ids
        ]

        evaluation_tests = load_jsonl(args.test_jsonl)

        results = run_reproduction_tests(
            instance_ids,
            patches,
            args.num_workers,
            args.run_id,
            args.instance_ids,
            args.timeout,
            testing_patches=True,
            apply_model_patch=False,
            test_jsonl=args.test_jsonl,
            dataset_name=args.dataset,
        )

        with open(args.test_jsonl.replace(".jsonl", "_verified.jsonl"), "w") as file:
            for evaluation_test in evaluation_tests:
                instance_id = evaluation_test["instance_id"]
                if instance_id in results and results[instance_id]:
                    evaluation_test["verified"] = True
                    file.write(json.dumps(evaluation_test) + "\n")
                else:
                    evaluation_test["verified"] = False
                    file.write(json.dumps(evaluation_test) + "\n")

    # instance_ids和patches: 生成的补丁, test_jsonl: 生成的test_patch, args.instance_ids: 需要运行的实例集合
    elif args.predictions_path == "gold":
        # check on groundtruth patches
        # for evaluation purposes
        ds = load_dataset(args.dataset)
        instance_ids = ds["test"]["instance_id"]
        patches = ds["test"]["patch"]

        results = run_reproduction_tests(
            instance_ids,
            patches,
            args.num_workers,
            args.run_id,
            args.instance_ids,
            args.timeout,
            testing_patches=False,
            apply_model_patch=True,
            test_jsonl=args.test_jsonl,
            dataset_name=args.dataset,
        )

        with open(
                "gold_production_test_results.json",
                "w",
        ) as file:
            file.write(json.dumps(results))

    else:
        # run on the agentless generated patches
        assert args.predictions_path.endswith("_processed.jsonl")
        with open(args.predictions_path, "r") as file:
            data_lines = [json.loads(line) for line in file]

        if args.load:
            reproduction_dict = {}
            for data in data_lines:
                instance_id = data["instance_id"]
                expected_output = "Issue resolved"
                path_to_log = f"logs/run_evaluation/{args.run_id}/test/{instance_id}/test_output.txt"
                if os.path.isfile(path_to_log):
                    passes_tests = txt_file_contains_string(
                        path_to_log, expected_output
                    )
                    reproduction_dict[instance_id] = passes_tests
                else:
                    reproduction_dict[instance_id] = False
        else:
            reproduction_dict = run_reproduction_for_each_instance(
                args, data_lines, args.run_id, args.test_jsonl
            )

        updated_data_lines = []
        for data in data_lines:
            instance_id = data["instance_id"]
            if instance_id in reproduction_dict:
                data["reproduction"] = reproduction_dict[instance_id]
            updated_data_lines.append(data)

        with open(
                args.predictions_path.replace(
                    "processed.jsonl", "reproduction_test_results.jsonl"
                ),
                "w",
        ) as file:
            for data in updated_data_lines:
                file.write(json.dumps(data) + "\n")


def _run_reproduction_tests_2(
        instance_ids,
        patches,
        num_workers,
        run_id,
        instance_ids_arg="",
        timeout=600,
        remove_docker_image=True,
        test_jsonl="",
        dataset_name="princeton-nlp/SWE-bench_Lite",
        testing=True,
        load=False,
        predictions_path=None,
):
    """
    Function to run reproduction tests based on directly provided parameters.

    Arguments:
    instance_ids -- List of instance IDs to run tests on
    patches -- List of patches corresponding to the instance IDs
    num_workers -- Number of workers for parallel execution
    run_id -- The ID for this run
    instance_ids_arg -- str: Instance IDs to run (space separated) (optional)
    timeout -- Timeout for each test run
    test_jsonl -- Path to the test JSONL file for test configuration
    dataset_name -- Name of the dataset to load
    testing -- Whether it's for testing or not (default is True)
    load -- Whether to load the results (default is False)
    predictions_path -- Path to the predictions file (optional)
    """

    if testing:
        # for reproduction test selection
        ds = load_dataset(dataset_name)
        instance_ids = ds["test"]["instance_id"]
        patches = [
            {"instance_id": instance_id, "patch": "", "normalized_patch": ""}
            for instance_id in instance_ids
        ]

        evaluation_tests = load_jsonl(test_jsonl)

        results = run_reproduction_tests(
            instance_ids,
            patches,
            num_workers,
            run_id,
            instance_ids_arg,
            timeout,
            testing_patches=True,
            apply_model_patch=False,
            remove_docker_image=remove_docker_image,
            test_jsonl=test_jsonl,
            dataset_name=dataset_name,
        )

        with open(test_jsonl.replace(".jsonl", "_verified.jsonl"), "w") as file:
            for evaluation_test in evaluation_tests:
                instance_id = evaluation_test["instance_id"]
                if instance_id in results and results[instance_id]:
                    evaluation_test["verified"] = True
                    file.write(json.dumps(evaluation_test) + "\n")
                else:
                    evaluation_test["verified"] = False
                    file.write(json.dumps(evaluation_test) + "\n")
        return test_jsonl.replace(".jsonl", "_verified.jsonl")

    elif predictions_path == "gold":
        # check on groundtruth patches
        # for evaluation purposes
        ds = load_dataset(dataset_name)
        instance_ids = ds["test"]["instance_id"]
        patches = ds["test"]["patch"]

        results = run_reproduction_tests(
            instance_ids,
            patches,
            num_workers,
            run_id,
            instance_ids_arg,
            timeout,
            testing_patches=False,
            apply_model_patch=True,
            remove_docker_image=remove_docker_image,
            test_jsonl=test_jsonl,
            dataset_name=dataset_name,
        )

        with open("gold_production_test_results.json", "w") as file:
            file.write(json.dumps(results))
        return "gold_production_test_results.json"

    else:
        # run on the model generated patches
        assert predictions_path.endswith("_diff.jsonl")
        with open(predictions_path, "r") as file:
            data_lines = [json.loads(line) for line in file]

        if load:
            reproduction_dict = {}
            for data in data_lines:
                instance_id = data["instance_id"]
                expected_output = "Issue resolved"
                path_to_log = f"logs/run_evaluation/{run_id}/test/{instance_id}/test_output.txt"
                if os.path.isfile(path_to_log):
                    passes_tests = txt_file_contains_string(path_to_log, expected_output)
                    reproduction_dict[instance_id] = passes_tests
                else:
                    reproduction_dict[instance_id] = False
        else:
            run_args = {
                "num_workers": num_workers,
                "instance_ids": instance_ids,
                "timeout": timeout,
                "dataset": dataset_name
            }
            reproduction_dict = run_reproduction_for_each_instance(
                type('Args', (), run_args), data_lines, run_id, test_jsonl, remove_docker_image
            )

        updated_data_lines = []
        for data in data_lines:
            instance_id = data["instance_id"]
            if instance_id in reproduction_dict:
                data["reproduction"] = reproduction_dict[instance_id]
            updated_data_lines.append(data)

        with open(
                predictions_path.replace(".jsonl", "_reproduction_test_results.jsonl"),
                "w",
        ) as file:
            for data in updated_data_lines:
                file.write(json.dumps(data) + "\n")

        return predictions_path.replace(".jsonl", "_reproduction_test_results.jsonl")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", type=str, required=True)
    parser.add_argument(
        "--testing", action="store_true", help="If true don't apply the model patch"
    )
    parser.add_argument(
        "--predictions_path",
        type=str,
        help="Patch file (or gold)",
    )
    parser.add_argument("--num_workers", type=int, default=12)
    parser.add_argument(
        "--timeout", type=int, default=600, help="Timeout for running tests in seconds"
    )
    parser.add_argument(
        "--instance_ids",
        nargs="+",
        type=str,
        help="Instance IDs to run (space separated)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="princeton-nlp/SWE-bench_Lite",
        choices=["princeton-nlp/SWE-bench_Lite", "princeton-nlp/SWE-bench_Verified"],
    )
    parser.add_argument("--test_jsonl", type=str)
    parser.add_argument("--load", action="store_true")

    args = parser.parse_args()

    # then load and run production tests on the results
    _run_reproduction_tests(args)


if __name__ == "__main__":
    main()

    # gold版本
    # python app/api/run_reproduction_tests.py --run_id test_gold --predictions_path gold --num_workers 4 --timeout 600 --instance_ids astropy__astropy-14365 django__django-11133 django__django-12856 sympy__sympy-18199 --test_jsonl experiment/example/output_0_processed_reproduction_test.jsonl  --dataset "princeton-nlp/SWE-bench_Lite"
    # testing reproduction
    # python app/api/run_reproduction_tests.py --run_id test_reproduction --num_workers 4 --testing --timeout 600 --instance_ids astropy__astropy-14365 django__django-11133 django__django-12856 sympy__sympy-18199 --test_jsonl experiment/example/output_0_processed_reproduction_test.jsonl  --dataset "princeton-nlp/SWE-bench_Lite"
    # agentless版本
