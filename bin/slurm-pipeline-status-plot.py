#!/usr/bin/env python

import sys
import re
import argparse
from pathlib import Path
import plotly.express as px  # type: ignore
from plotly.io import write_image, write_html  # type: ignore

from slurm_pipeline.status import SlurmPipelineStatusCollection

# NOTE: the order in the following set is important: it determines the legend order.
#
# These values are (mainly) taken from px.colors.qualitative.Plotly described at
# https://plotly.com/python/discrete-color/
STATUS_COLORS = {
    "SUSPENDED": "#FECB52",
    "REVOKED": "#FD3216",
    "RESIZING": "#AB63FA",
    "REQUEUED": "#FB00D1",
    "PREEMPTED": "#54A24B",
    "NODE_FAIL": "#77B7B2",
    "DEADLINE": "#FFA15A",
    "BOOT_FAIL": "#19D3F3",
    "CANCELLED": "#BAB0AC",
    "OUT_OF_MEMORY": "#FF97FF",
    "TIMEOUT": "#FF6692",
    "FAILED": "#EF553B",
    "COMPLETED": "#00CC96",
    "RUNNING": "#636EFA",
    "PENDING": "#B6E880",
}

# Sanity check that there are no repeated colors.
assert len(set(STATUS_COLORS.values())) == len(STATUS_COLORS)


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a plot showing the progress of a SLURM pipeline run (or runs)."
        ),
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
        "--title",
        help="The overall plot title.",
        metavar="TITLE",
    )

    parser.add_argument(
        "--xtitle",
        default="Pipeline step",
        help="The x-axis title.",
        metavar="TITLE",
    )

    parser.add_argument(
        "--ytitle",
        default="Count",
        help="The y-axis title.",
        metavar="TITLE",
    )

    parser.add_argument(
        "--image",
        help="An (optional) output image file. Output format is set according to file suffix.",
        metavar="FILE.png",
    )

    return parser.parse_args()


def main() -> None:
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

    if args.title is not None:
        title = args.title
    else:
        if len(names) > 1:
            title = f"Pipeline task summary for {len(names)} separate runs"
        else:
            title = "Pipeline task summary"

    # Add a column full of 1s that we will put on the y-axis to show the count of tasks
    # at each step.
    spsc.df["one"] = 1

    fig = px.bar(
        data_frame=spsc.df,
        x="step",
        y="one",
        color="status",
        color_discrete_map=STATUS_COLORS,
        title=title,
        hover_name="name",
        # Note: the order in hover_data is the order that will appear in the hover box.
        hover_data={
            "status": True,
            "step": True,
            "node": True,
            "elapsed": True,
            "jobId": True,
            "name": False,
            "name": False,
            "one": False,
            "seconds": False,
        },
        category_orders={
            "step": spsc.nonEmptyStepNames,
            "status": list(STATUS_COLORS),
        },
    )

    fig.update_layout(
        xaxis={"title": args.xtitle},
        yaxis={"title": args.ytitle},
    )

    if args.image:
        write_image(fig, args.image)

    if args.html:
        write_html(fig, args.html)


if __name__ == "__main__":
    main()
