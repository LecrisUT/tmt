import webbrowser
from typing import Optional

from jinja2 import select_autoescape

import tmt
import tmt.log
import tmt.options
import tmt.steps
import tmt.steps.report
import tmt.utils
import tmt.utils.templates
from tmt.container import container, field
from tmt.utils import Path

HTML_TEMPLATE_PATH = tmt.utils.resource_files('steps/report/html/template.html.j2')


@container
class ReportHtmlData(tmt.steps.report.ReportStepData):
    open: bool = field(
        default=False,
        option=('-o', '--open'),
        is_flag=True,
        help='Open results in your preferred web browser.'
        )

    absolute_paths: bool = field(
        default=False,
        option='--absolute-paths',
        is_flag=True,
        help='Make paths absolute rather than relative to working directory.'
        )

    display_guest: str = field(
        default='auto',
        option='--display-guest',
        metavar='auto|always|never',
        choices=['auto', 'always', 'never'],
        help="""
             When to display full guest name in report: when more than a single guest was involved
             (default), always, or never.
             """)


@tmt.steps.provides_method('html')
class ReportHtml(tmt.steps.report.ReportPlugin[ReportHtmlData]):
    """
    Format test results into an HTML report.

    Example config:

    .. code-block:: yaml

        report:
            how: html
            open: true
    """

    _data_class = ReportHtmlData

    def prune(self, logger: tmt.log.Logger) -> None:
        """ Do not prune generated html report """

    def go(self, *, logger: Optional[tmt.log.Logger] = None) -> None:
        """ Process results """
        super().go(logger=logger)

        # Prepare the template
        environment = tmt.utils.templates.default_template_environment()

        # Explicitly enable the autoescape because it's disabled by default by TMT
        # (see /teemtee/tmt/issues/2873 for more info.
        environment.autoescape = select_autoescape(enabled_extensions=('html.j2'))

        if self.data.absolute_paths:
            def _linkable_path(path: str) -> str:
                return str(Path(path).absolute())

            environment.filters["linkable_path"] = _linkable_path
        else:
            # Links used in html should be relative to a workdir
            def _linkable_path(path: str) -> str:
                assert self.workdir is not None  # narrow type

                return str(Path(path).relative_to(self.workdir))

            environment.filters["linkable_path"] = _linkable_path

        if self.data.display_guest == 'always':
            display_guest = True

        elif self.data.display_guest == 'never':
            display_guest = False

        else:
            seen_guests = {
                result.guest.name
                for result in self.step.plan.execute.results()
                }

            display_guest = len(seen_guests) > 1

        # Write the report
        filename = Path('index.html')

        self.write(
            filename,
            data=tmt.utils.templates.render_template_file(
                HTML_TEMPLATE_PATH,
                environment,
                results=self.step.plan.execute.results(),
                base_dir=self.step.plan.execute.workdir,
                plan=self.step.plan,
                display_guest=display_guest))

        # Nothing more to do in dry mode
        if self.is_dry_run:
            return

        # Show output file path
        assert self.workdir is not None
        target = self.workdir / filename
        self.info("output", target, color='yellow')
        if not self.data.open:
            return

        # Open target in webbrowser
        try:
            if webbrowser.open(f"file://{target}", new=0):
                self.info(
                    'open', 'Successfully opened in the web browser.',
                    color='green')
                return
            self.fail("Failed to open the web browser.")
        except Exception as error:
            self.fail(f"Failed to open the web browser: {error}")

        raise tmt.utils.ReportError("Unable to open the web browser.")
