# /test/test_jobstamps.py
#
# Unit tests for the jobstamps module.
#
# See /LICENCE.md for Copyright information
"""Unit tests for the jobstamps module."""

import os

import shutil

import time

from test import testutil

from jobstamps import jobstamp

from mock import Mock, call

from nose_parameterized import param, parameterized

from testtools import ExpectedException
from testtools.matchers import DirExists


class MockJob(Mock):

    """Wraps Mock to provide __name__ attribute."""

    def __init__(self, *args, **kwargs):
        """Pass __name__ attribute to __init__."""
        super(MockJob, self).__init__(*args, __name__="job", **kwargs)
        self.return_value = None


def _update_method_doc(func, num, params):
    """Format docstring for tests with different update methods."""
    del num

    if params[0][0] is jobstamp.MTimeMethod:
        return func.__doc__[:-1] + """ using Modification Time Method."""
    elif params[0][0] is jobstamp.HashMethod:
        return func.__doc__[:-1] + """ using Hash Method."""


class TestJobstamps(testutil.InTemporaryDirectoryTestBase):

    """TestCase for jobstamps module."""

    _METHODS = (param(jobstamp.MTimeMethod), param(jobstamp.HashMethod))

    def test_raise_if_cachedir_exists_as_file(self):  # suppress(no-self-use)
        """Raise IOError if specified cache dir exists and is a file."""
        cache_entry = os.path.join(os.getcwd(), "cache")
        with open(cache_entry, "w") as cache_entry_file:
            cache_entry_file.write("Regular file")

        with ExpectedException(IOError):
            jobstamp.run(lambda: None,
                         jobstamps_cache_output_directory=cache_entry)

    def test_running_job_creates_cache_directory(self):
        """Running job creates stamp file directory."""
        os.chdir("..")

        cache_directory = self._temporary_directory
        shutil.rmtree(cache_directory)

        job = MockJob()
        jobstamp.run(job, 1, jobstamps_cache_output_directory=cache_directory)
        self.assertThat(cache_directory, DirExists())

    def test_can_create_cache_directory_in_nested_directories(self):
        """Running job creates stamp file directory, even if nested."""
        os.chdir("..")

        cache_directory = os.path.join(self._temporary_directory, "nested")
        shutil.rmtree(self._temporary_directory)

        job = MockJob()
        jobstamp.run(job, 1, jobstamps_cache_output_directory=cache_directory)
        self.assertThat(cache_directory, DirExists())

    @parameterized.expand(_METHODS, testcase_func_doc=_update_method_doc)
    def test_running_job_returns_expected_value(self, method):
        """Job is run initially when there is no stamp."""
        job = MockJob()
        job.return_value = "expected"
        value = jobstamp.run(job,
                             1,
                             jobstamps_cache_output_directory=os.getcwd(),
                             jobstamps_method=method)
        self.assertEqual(value, job.return_value)

    @parameterized.expand(_METHODS, testcase_func_doc=_update_method_doc)
    def test_running_job_twice_returns_expected_value(self, method):
        """Job is run again when there is no stamp."""
        job = MockJob()
        job.return_value = "expected"
        jobstamp.run(job,
                     1,
                     jobstamps_cache_output_directory=os.getcwd(),
                     jobstamps_method=method)
        value = jobstamp.run(job,
                             1,
                             jobstamps_cache_output_directory=os.getcwd())
        self.assertEqual(value, job.return_value)

    def test_running_job_once_runs_job(self):  # suppress(no-self-use)
        """Job is run initially when there is no stamp."""
        job = MockJob()
        jobstamp.run(job, 1, jobstamps_cache_output_directory=os.getcwd())

        job.assert_called_with(1)

    @parameterized.expand(_METHODS, testcase_func_doc=_update_method_doc)
    # suppress(no-self-use)
    def test_running_job_twice_only_runs_underlying_job_once(self, method):
        """Job is not run twice when there are no deps and already stamped."""
        job = MockJob()
        jobstamp.run(job,
                     1,
                     jobstamps_cache_output_directory=os.getcwd(),
                     jobstamps_method=method)
        jobstamp.run(job,
                     1,
                     jobstamps_cache_output_directory=os.getcwd(),
                     jobstamps_method=method)

        job.assert_called_once_with(1)

    @parameterized.expand(_METHODS, testcase_func_doc=_update_method_doc)
    # suppress(no-self-use)
    def test_running_job_with_different_args_runs_it_again(self, method):
        """Job can be run twice with different args."""
        job = MockJob()
        jobstamp.run(job,
                     1,
                     jobstamps_cache_output_directory=os.getcwd(),
                     jobstamps_method=method)
        jobstamp.run(job,
                     2,
                     jobstamps_cache_output_directory=os.getcwd(),
                     jobstamps_method=method)

        job.assert_has_calls([call(1), call(2)])

    @parameterized.expand(_METHODS, testcase_func_doc=_update_method_doc)
    # suppress(no-self-use)
    def test_job_runs_again_when_dependency_doesnt_exist(self, method):
        """Job can be run twice with different args when dep doesn't exist."""
        job = MockJob()
        dependency = os.path.join(os.getcwd(), "dependency")

        jobstamp.run(job,
                     1,
                     jobstamps_dependencies=[dependency],
                     jobstamps_cache_output_directory=os.getcwd(),
                     jobstamps_method=method)
        jobstamp.run(job,
                     1,
                     jobstamps_dependencies=[dependency],
                     jobstamps_cache_output_directory=os.getcwd(),
                     jobstamps_method=method)

        job.assert_has_calls([call(1), call(1)])

    @parameterized.expand(_METHODS, testcase_func_doc=_update_method_doc)
    # suppress(no-self-use)
    def test_job_runs_once_only_once_when_dependency_up_to_date(self, method):
        """Job runs only once when stamp is more recent than dependency."""
        job = MockJob()
        dependency = os.path.join(os.getcwd(), "dependency")
        with open(dependency, "w") as dependency_file:
            dependency_file.write("Contents")

        jobstamp.run(job,
                     1,
                     jobstamps_dependencies=[dependency],
                     jobstamps_cache_output_directory=os.getcwd(),
                     jobstamps_method=method)
        jobstamp.run(job,
                     1,
                     jobstamps_dependencies=[dependency],
                     jobstamps_cache_output_directory=os.getcwd(),
                     jobstamps_method=method)

        job.assert_called_once_with(1)

    @parameterized.expand(_METHODS, testcase_func_doc=_update_method_doc)
    # suppress(no-self-use)
    def test_job_runs_again_when_dependency_not_up_to_date(self, method):
        """Job runs again when dependency is more recent than stamp."""
        job = MockJob()
        dependency = os.path.join(os.getcwd(), "dependency")
        with open(dependency, "w") as dependency_file:
            dependency_file.write("Contents")

        jobstamp.run(job,
                     1,
                     jobstamps_dependencies=[dependency],
                     jobstamps_cache_output_directory=os.getcwd(),
                     jobstamps_method=method)

        time.sleep(1)

        with open(dependency, "w") as dependency_file:
            dependency_file.write("Updated")

        jobstamp.run(job,
                     1,
                     jobstamps_dependencies=[dependency],
                     jobstamps_cache_output_directory=os.getcwd())

        job.assert_has_calls([call(1), call(1)])

    @parameterized.expand(_METHODS, testcase_func_doc=_update_method_doc)
    # suppress(no-self-use)
    def test_job_runs_again_when_dependency_deleted(self, method):
        """Job runs again when dependency is later deleted."""
        job = MockJob()
        dependency = os.path.join(os.getcwd(), "dependency")
        with open(dependency, "w") as dependency_file:
            dependency_file.write("Contents")

        jobstamp.run(job,
                     1,
                     jobstamps_dependencies=[dependency],
                     jobstamps_cache_output_directory=os.getcwd(),
                     jobstamps_method=method)

        os.remove(dependency)

        jobstamp.run(job,
                     1,
                     jobstamps_dependencies=[dependency],
                     jobstamps_cache_output_directory=os.getcwd())

        job.assert_has_calls([call(1), call(1)])

    # suppress(no-self-use)
    def test_job_runs_again_when_output_file_doesnt_exist(self):
        """Job can be run twice when output file doesn't exist."""
        job = MockJob()
        expected_outputs = os.path.join(os.getcwd(), "expected_output")

        jobstamp.run(job,
                     1,
                     jobstamps_output_files=[expected_outputs],
                     jobstamps_cache_output_directory=os.getcwd())
        jobstamp.run(job,
                     1,
                     jobstamps_output_files=[expected_outputs],
                     jobstamps_cache_output_directory=os.getcwd())

        job.assert_has_calls([call(1), call(1)])

    # suppress(no-self-use)
    def test_job_runs_once_when_output_file_exists(self):
        """Job runs only once when output file exists."""
        job = MockJob()
        expected_outputs = os.path.join(os.getcwd(), "expected_output")

        jobstamp.run(job,
                     1,
                     jobstamps_output_files=[expected_outputs],
                     jobstamps_cache_output_directory=os.getcwd())

        with open(expected_outputs, "w") as expected_outputs_file:
            expected_outputs_file.write("Expected output")

        jobstamp.run(job,
                     1,
                     jobstamps_output_files=[expected_outputs],
                     jobstamps_cache_output_directory=os.getcwd())

        job.assert_called_once_with(1)
