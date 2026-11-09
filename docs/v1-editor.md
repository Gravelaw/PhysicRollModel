# V1 local scenario editor

Start the editor with an explicit destination for new runs:

```bash
python -m physicroll.editor --runs-dir /workspace/physicroll-data/runs/editor
```

Open the printed `127.0.0.1` address on the same computer. The server binds
only to loopback, uses no remote service or external browser assets, and stops
with Ctrl-C. In a headless cloud environment, use the RunSpec and bundle CLI
instead unless an approved local browser route is available.

Choose **Guided synthetic checked pass** to edit named SI scenario values and
the bounded spatial cell count. The form labels entry speed and exit gauge as
prescribed inputs. Its mean-flow-stress field is only a positive domain guard;
the selected fixed synthetic power-hardening law controls calculated stress.
The editor keeps the requested and resolved scenario records aligned,
and records a hash of the embedded edited scenario. **Check inputs and
execution** runs the checked workflow without saving; validation or solver
errors appear above the form with the entered values preserved. **Save verified
run** publishes a new run bundle and opens its verified summary. Existing runs
can be reopened as a new edit; the original run is not overwritten. The saved
offline report is available from the summary.

The other packaged W3 examples open as versioned RunSpec JSON. This gives a
checked route for finite search, frozen conditional benchmark/sensitivity and
offline operating-phase replay. Their declarations and resources have workflow
specific constraints; the editor reports those errors and preserves invalid
JSON text for correction. The frozen Shao examples are comparisons, not
calibration forms. No observed or machine data is supplied by the editor.

Run directories are generated identifiers beneath `--runs-dir`; browser form
input cannot select an arbitrary output path. A session token guards writes,
and the server rejects foreign or duplicate Host headers and foreign POST
origins. It is intended for the same computer, not network exposure.
The saved-run page verifies the bundle before displaying its report.
The editor is an interface for the current checked workflows. The required
time-resolved solver and dynamic Blender/USD playback are separate v1 gates;
this form does not claim to predict them.
