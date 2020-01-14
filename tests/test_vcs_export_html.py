import os
import unittest


def debug_print(s):
    DEBUG = True
    if DEBUG:
        print(s)


def assert_image_tag_present(html_file):
    debug_print('Assert image tag is present')
    image_tag_present = False
    with open(html_file, 'r') as f:
        for line in f:
            # This tag appears in the html if SLIDERS_ENABLED = False
            # However, the images still appear in the html if SLIDERS_ENABLED = True,
            # yet this tag does not.
            if '<img' in line:
                image_tag_present = True
    assert image_tag_present


# Move these to jupyter-vcdat?
# Use Selenium?
class TestVCSExportHTML(unittest.TestCase):
    def testExportHTML(self):
        debug_print('Run the notebook')
        # This is apparently NOT equivalent to running the notebook on the web.
        # Generating the HTML this way keeps the plot, whereas running from the web does not.
        assert os.system('jupyter nbconvert --to notebook --execute ../test_export_html.ipynb') == 0
        debug_print('Run equivalent to clicking "Download as"')
        assert os.system('jupyter nbconvert --to html ../test_export_html.nbconvert.ipynb') == 0
        debug_print('Move HTML file')
        assert os.system('mv ../test_export_html.nbconvert.html test_export_html.html') == 0
        assert_image_tag_present('test_export_html.html')

    def testExportHTMLWithExecute(self):
        debug_print('Execute and convert the notebook in one step')
        assert os.system('jupyter nbconvert --to html --execute ../test_export_html.ipynb') == 0
        debug_print('Move HTML file')
        assert os.system('mv ../test_export_html.html test_export_html_with_execute.html') == 0
        assert_image_tag_present('test_export_html_with_execute.html')

    def tearDown(self):
        os.system('rm {}'.format('../test_export_html.nbconvert.ipynb'))
        os.system('rm {}'.format('test_export_html.html'))
        os.system('rm {}'.format('test_export_html_with_execute.html'))


if __name__ == '__main__':
    # Both of these tests
    # pass if SLIDERS_ENABLED = False
    # and fail if SLIDERS_ENABLED = True
    t = TestVCSExportHTML()
    debug_print('Export HTML with execute')
    t.testExportHTMLWithExecute()
    debug_print('Export HTML')
    t.testExportHTML()
    t.tearDown()
    debug_print('Done')
