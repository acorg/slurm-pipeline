#!/usr/bin/env python

import sys
import re
import argparse
from pathlib import Path
import plotly.express as px
from plotly.io import write_image, write_html

from slurm_pipeline.status import SlurmPipelineStatusCollection

STATUS_ORDER = (
    "SUSPENDED",
    "REVOKED",
    "RESIZING",
    "REQUEUED",
    "PREEMPTED",
    "NODE_FAIL",
    "DEADLINE",
    "BOOT_FAIL",
    "OUT_OF_MEMORY",
    "TIMEOUT",
    "FAILED",
    "CANCELLED",
    "PENDING",
    "COMPLETED",
    "RUNNING",
)


def parseArgs():
    parser = argparse.ArgumentParser(
        description="Create a plot showing the progress of a SLURM pipeline run.",
    )

    parser.add_argument(
        "statusFiles",
        nargs="+",
        metavar="status1.json [status2.json, ...]",
        help="The JSON (files previously created by slurm-pipeline.py) to examine.",
    )

    parser.add_argument(
        "--nameRegex",
        metavar="REGEX",
        help=(
            "A regex with a single capture group to use to extract the name to "
            "associate with each status file. The regex will be matched against the "
            "status filenames. If not given, the parent directory of each "
            "specification status file will be used as its name."
        ),
    )

    parser.add_argument(
        "--html",
        help="The (optional) output HTML file.",
        metavar="FILE.html",
    )

    parser.add_argument(
        "--image",
        help="An (optional) output image file. Output format is set according to file suffix.",
        metavar="FILE.png",
    )

    return parser.parse_args()


def main():
    """
    Make a plotly HTML and/or image to show the status of all samples in a pipeline run.
    """
    args = parseArgs()

    if not (args.html or args.image):
        sys.exit(
            "You need to specify at least one of --html or --image, "
            "otherwise I have nothing to do! Exiting."
        )

    nameRegex = re.compile(args.nameRegex) if args.nameRegex else None
    names = []

    for filename in args.statusFiles:
        if nameRegex:
            match = nameRegex.match(filename)
            if match:
                name = match.group(1)
            else:
                sys.exit(f"The name regex did not match filename {filename!r}.")
        else:
            name = Path(filename).parent.name

        names.append(name)

    spsc = SlurmPipelineStatusCollection(args.statusFiles, names)

    fig = px.bar(
        data_frame=spsc.df,
        x="step",
        y="seconds",
        color="status",
        title="Pipeline status",
        hover_data={
            "status": True,
            "name": False,
            "step": False,
            "seconds": False,
            "node": True,
            "elapsed": True,
            "jobId": True,
        },
        text="name",
        category_orders={
            "step": spsc.stepNames,
            "status": STATUS_ORDER,
        },
    )

    fig.update_layout(
        yaxis={"title": "Total seconds"},
        xaxis={"title": "Pipeline step"},
    )

    if args.image:
        write_image(fig, args.image)

    if args.html:
        write_html(fig, args.html)


if __name__ == "__main__":
    main()
