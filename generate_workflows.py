import json
from functools import cache
from pathlib import Path
from typing import Iterator, Never

import fsspec
import yaml
from loguru import logger

THIS_DIR = Path(__file__).parent
WORKFLOWS_DIR = THIS_DIR / "workflows"


class IncompatibleLayerError(NotImplementedError):
    """A layer is not compatible with the current migration code."""


@cache
def lockfile_data() -> dict:
    """Fetch the QGreenland configuration lock file and load it."""
    QGREENLAND_TAG: Final = "v3.0.0"
    QGREENLAND_CONFIG_LOCK_URL: Final = (
        "https://raw.githubusercontent.com/nsidc/qgreenland"
        f"/{QGREENLAND_TAG}/qgreenland/config/cfg-lock.json"
    )

    with fsspec.open(QGREENLAND_CONFIG_LOCK_URL) as file:
        lockfile_data = json.loads(file.read())

    return lockfile_data


@cache
def datasets() -> dict:
    """Return the datasets in the QGreenland config lock file."""
    return lockfile_data()["datasets"]


@cache
def layer_tree() -> dict:
    """Return the layer tree in the QGreenland config lock file."""
    return lockfile_data()["layer_tree"]


def layers_from_tree_node(layer_tree_node: dict) -> Iterator[dict]:
    """Flatten the layer tree to a list of layers.

    For the purposes of generating data transformation recipes, we don't care about the
    hierarchy! That's purely QGreenland's domain.
    """
    if "layer_cfg" in layer_tree_node:
        # It's a layer, not a group
        yield {
            "name": layer_tree_node["name"],
            "config": layer_tree_node["layer_cfg"],
        }

    if "children" in layer_tree_node:
        # It's a group
        for child_layer in layer_tree_node["children"]:
            yield from layers_from_tree_node(child_layer)


def transform_step(*, layer: dict, step_number: int) -> dict:
    """Generate Argo workflow "step" from a QGreenland config lock file step.

    This is pretty smelly to me; needs refactoring.

    We assume (at least...):
        * One directory slug can be used in a given arg
        * When directory slugs are used in an arg, they are always used in the form
          "{slug}/some_filename.ext", with nothing else present.
    """
    INPUT_DIR: Final = "/tmp/input_dir"
    ASSETS_DIR: Final = "/tmp/assets_dir"
    OUTPUT_DIR: Final = "/tmp/output_dir"
    ASSETS_URL: Final = 'https://raw.githubusercontent.com/nsidc/qgreenland/v3.0.0/qgreenland/assets'

    STEP: Final = layer["config"]["steps"][step_number]
    step_id: Final = lambda step_num: f"step-{step_num}"
    output_artifact_name: Final = lambda step_num: f"{step_id(step_num)}-output_dir"
    input_artifact_name: Final = lambda step_num: f"{step_id(step_num)}-input_dir"
    assets_artifact_name: Final = lambda step_num: f"{step_id(step_num)}-assets_dir"

    args = []
    inputs = []
    for arg in STEP["args"][1:]:
        args.append(arg.format(
            input_dir=INPUT_DIR,
            assets_dir=ASSETS_DIR,
            output_dir=OUTPUT_DIR,
        ))

        if "{input_dir}" in arg:
            if step_number == 0:
                # Add the input "asset"
                dataset = datasets()[layer["config"]["input"]["dataset"]["id"]]
                asset = dataset["assets"][layer["config"]["input"]["asset"]["id"]]
                try:
                    asset_filepath = asset["filepath"]
                except KeyError:
                    raise IncompatibleLayerError(
                        f"Layer {layer['name']} asset has no filepath."
                    )

                fn = arg.split("/", 1)[1]

                inputs.append({
                    "name": input_artifact_name(step_number),
                    "path": f"{INPUT_DIR}/{fn}",
                    "http": {"url": f"{ASSETS_URL}/{fn}"},
                })
            else:
                # Add output dir artifact from previous step
                inputs.append({
                    "name": input_artifact_name(step_number),
                    "from": f"{{{{ steps.{step_id(step_number-1)}.outputs.artifacts.{output_artifact_name(step_number-1)} }}}}",
                })
        elif "{assets_dir}" in arg:
            fn = arg.split("/", 1)[1]
            inputs.append({
                "name": assets_artifact_name(step_number),
                "path": f"{ASSETS_DIR}/{fn}",
                "http": {"url": f"{ASSETS_URL}/{fn}"},
            })


    step_manifest = {
        "name": step_id(step_number),
        "inline": {
            "container": {
                "image": "ghcr.io/osgeo/gdal:alpine-normal-3.9.0",
                "command": [STEP["args"][0]],
                "args": args,
                "volumeMounts": [{
                    "name": "output-mount",
                    "mountPath": OUTPUT_DIR,
                }],
            },
            # The emptyDir volume ensures the output artifact directory exists and is ready
            # to receive data
            "volumes": [{
                "name": "output-mount",
                "emptyDir": {},
            }],
        },
    }

    if inputs:
        step_manifest["inline"]["inputs"] = {"artifacts": inputs}


    # NOTE: I didn't include this in the original construction because I want outputs to
    # be after inputs.
    step_manifest["inline"]["outputs"] = {
        "artifacts": [{
            "name": output_artifact_name(step_number),
            "path": OUTPUT_DIR,
        }],
    }

    return step_manifest


def transform_steps(layer: dict) -> list[list[dict]]:
    """Generate Argo workflow "steps" from steps in QGreenland's config lock file."""
    steps = []
    for step_number, _ in enumerate(layer["config"]["steps"]):
        steps.append([transform_step(
            layer=layer,
            step_number=step_number,
        )])

    return steps


def _workflow_from_layer(layer: dict) -> dict:
    """Generate an Argo workflow manifest from a layer configuration's steps."""
    steps = transform_steps(layer)

    manifest = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Workflow",
        "metadata": {
            "generateName": f"ogdc-recipe-{layer['config']['id'].replace('_', '-')}-",
            # TODO: What is this label?
            "labels": {"workflows.argoproj.io/archive-strategy": "false"},
            "annotations": {
                "workflows.argoproj.io/description": layer["config"]["description"],
                "qgreenlandLayerId": layer["name"],
            }
        },
        "spec": {
            # The name of the template that will be executed first
            "entrypoint": "main",
            "templates": [
                {
                    "name": "main",
                    "steps": steps,
                },
            ],
        }
    }
    return manifest


def reject_incompatible_layer(layer: dict) -> Never:
    """Handle complexities we're not ready for yet."""
    steps = layer["config"]["steps"]

    if not steps:
        raise IncompatibleLayerError(
            f"Layer {layer['name']} has no steps; probably an online layer."
        )

    for step in steps:
        cmd = step["args"][0]

        if not any(
            cmd.startswith(valid_prefix)
            for valid_prefix in ("gdal", "ogr2ogr")
        ):
            raise IncompatibleLayerError(
                f"Layer {layer['name']} step starts with incompatible command: {cmd}"
            )


def workflow_from_locked_layer(layer: dict) -> dict:
    """Generate an Argo Workflow manifest from a layer config."""
    reject_incompatible_layer(layer)

    return _workflow_from_layer(layer)


def workflows_from_locked_layers() -> any:
    """Generate Argo workflow configuration from QGreenland configuration lock file."""
    layers = list(layers_from_tree_node(layer_tree()))
    assert len(layers) == 398

    for layer in layers:
        try:
            yield workflow_from_locked_layer(layer)
        except IncompatibleLayerError as e:
            logger.warning(e)


def main() -> None:
    workflows = list(workflows_from_locked_layers())
    assert len(workflows) == 24

    # Write workflows to YAML files
    for workflow in workflows:
        output_fn = f"{workflow['metadata']['annotations']['qgreenlandLayerId']}.yml"
        output_file = WORKFLOWS_DIR / output_fn
        output_file.write_text(yaml.dump(workflow, sort_keys=False))


if __name__ == "__main__":
    main()
