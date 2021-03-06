#!/usr/bin/env python
import os
import sys
import cdat_info


class VCSTestRunner(cdat_info.TestRunnerBase):
    def _prep_nose_options(self):
        opt = super(VCSTestRunner, self)._prep_nose_options()
        if self.args.no_vtk_ui:
            opt += ["-A",  "not vtk_ui"]
        if self.args.vtk is not None:
            cdat_info.run_command(
                "conda install -f -y -c {} vtk-cdat".format(self.args.vtk))
        return opt


test_suite_name = 'vcs'

workdir = os.getcwd()
runner = VCSTestRunner(test_suite_name, options=["--no-vtk-ui", "--vtk"],
                       options_files=["tests/vcs_runtests.json"],
                       get_sample_data=True,
                       test_data_files_info="share/test_data_files.txt")
ret_code = runner.run(workdir)

sys.exit(ret_code)
