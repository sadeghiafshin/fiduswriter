import os
import time
import multiprocessing
from random import randrange
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from django.conf import settings
from test.testcases import LiveTornadoTestCase
from editor_helper import EditorHelper


class OneUserTwoBrowsersTests(LiveTornadoTestCase, EditorHelper):
    """
    Tests in which collaboration between two browsers with the same user logged
    into both browsers.
    """
    user = None
    TEST_TEXT = "Lorem ipsum dolor sit amet."
    MULTILINE_TEST_TEXT = "Lorem ipsum\ndolor sit amet."
    fixtures = []

    @classmethod
    def setUpClass(cls):
        super(OneUserTwoBrowsersTests, cls).setUpClass()
        driver_data = cls.get_drivers(2)
        cls.driver = driver_data["drivers"][0]
        cls.driver2 = driver_data["drivers"][1]
        cls.client = driver_data["clients"][0]
        cls.client2 = driver_data["clients"][1]
        cls.wait_time = driver_data["wait_time"]

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()
        cls.driver2.quit()
        super(OneUserTwoBrowsersTests, cls).tearDownClass()

    def setUp(self):
        self.user = self.create_user()
        self.login_user(self.user, self.driver, self.client)
        self.login_user(self.user, self.driver2, self.client2)
        self.doc = self.create_new_document()

    def get_title(self, driver):
        # Title is child 0.
        return driver.execute_script(
            'return window.theEditor.pm.doc.firstChild'
            '.content.content[0].textContent;'
        )

    def get_contents(self, driver):
        # Contents is child 5.
        return driver.execute_script(
            'return window.theEditor.pm.doc.firstChild'
            '.content.content[5].textContent;'
        )

    def test_typing(self):
        """
        Test typing in collaborative mode with one user using browser windows
        with the user typing separately at small, random intervals.
        """
        self.load_document_editor(self.driver, self.doc)
        self.load_document_editor(self.driver2, self.doc)

        document_input = self.driver.find_element_by_class_name(
            'ProseMirror-content'
        )
        document_input2 = self.driver2.find_element_by_class_name(
            'ProseMirror-content'
        )

        # Chrome with selenium has problem with focusing elements, so we use
        # the ProseMirror internal methods for this.
        # First start tag is length 1, so placing after first start tag is
        # position 1
        self.driver.execute_script(
            'window.theEditor.pm.setTextSelection(2,2)')
        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(2,2)')

        first_part = "Here is "
        second_part = "my title"

        for i in range(8):
            document_input.send_keys(second_part[i])
            time.sleep(randrange(30, 40) / 200.0)
            document_input2.send_keys(first_part[i])
            time.sleep(randrange(30, 40) / 200.0)

        self.assertEqual(
            16,
            len(self.get_title(self.driver))
        )

        self.assertEqual(
            self.get_title(self.driver2),
            self.get_title(self.driver)
        )

        # Chrome with selenium has problem with focusing elements, so we use
        # the ProseMirror internal methods for this.
        # Original document length was 16 (1 for each start/end tag of fields
        # with plaintext and 2 for richtext fields - abstract and contents).
        # Cursor needs to be in last element, so -2 for last end tag.
        # Added content is 16 characters long, so + 16.
        # Total: 30.
        self.driver.execute_script(
            'window.theEditor.pm.setTextSelection(31,31)')
        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(31,31)')

        for char in self.TEST_TEXT:
            document_input.send_keys(char)
            time.sleep(randrange(30, 40) / 200.0)
            document_input2.send_keys(char)
            time.sleep(randrange(30, 40) / 200.0)

        self.assertEqual(
            len(self.TEST_TEXT) * 2,
            len(self.get_contents(self.driver))
        )

        self.assertEqual(
            self.get_contents(self.driver2),
            self.get_contents(self.driver)
        )

    def test_threaded_typing(self):
        """
        Test typing in collaborative mode with one user using browser windows
        with the user typing simultaneously in two different threads.
        """
        self.load_document_editor(self.driver, self.doc)
        self.load_document_editor(self.driver2, self.doc)

        document_input = self.driver.find_element_by_class_name(
            'ProseMirror-content'
        )
        document_input2 = self.driver2.find_element_by_class_name(
            'ProseMirror-content'
        )
        # Chrome with selenium has problem with focusing elements, so we use
        # the ProseMirror internal methods for this.
        # First start tag is length 1, so placing after first start tag is
        # position 1
        self.driver.execute_script(
            'window.theEditor.pm.setTextSelection(2,2)')
        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(2,2)')

        first_part = "Here is "
        second_part = "my title"

        p1 = multiprocessing.Process(
            target=self.input_text,
            args=(document_input, second_part)
        )
        p2 = multiprocessing.Process(
            target=self.input_text,
            args=(document_input2, first_part)
        )
        p1.start()
        p2.start()
        p1.join()
        p2.join()

        # Wait for the two editors to be synched
        self.wait_for_doc_sync(self.driver, self.driver2)

        self.assertEqual(
            16,
            len(self.get_title(self.driver))
        )

        self.assertEqual(
            self.get_title(self.driver2),
            self.get_title(self.driver)
        )

        # Chrome with selenium has problem with focusing elements, so we use
        # the ProseMirror internal methods for this.
        # Original document length was 16 (1 for each start/end tag of fields
        # with plaintext and 2 for richtext fields - abstract and contents).
        # Cursor needs to be in last element, so -2 for last end tag.
        # Added content is 16 characters long, so + 16.
        # Total: 30.
        self.driver.execute_script(
            'window.theEditor.pm.setTextSelection(31,31)')
        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(31,31)')

        p1 = multiprocessing.Process(
            target=self.input_text,
            args=(document_input, self.TEST_TEXT)
        )
        p2 = multiprocessing.Process(
            target=self.input_text,
            args=(document_input2, self.TEST_TEXT)
        )
        p1.start()
        p2.start()
        p1.join()
        p2.join()

        # Wait for the two editors to be synched
        self.wait_for_doc_sync(self.driver, self.driver2)

        self.assertEqual(
            len(self.TEST_TEXT) * 2,
            len(self.get_contents(self.driver))
        )

        self.assertEqual(
            self.get_contents(self.driver2),
            self.get_contents(self.driver)
        )

    def make_bold(self, driver):
        button = driver.find_element_by_id('button-bold')
        button.click()

    def get_boldtext(self, driver):
        btext = driver.find_element_by_xpath(
            '//*[contains(@class, "article-body")]/p/strong')
        return btext.text

    def test_select_and_bold(self):
        """
        Test typing in collaborative mode with one user typing and
        another user bold some part of the text in two different threads.
        """
        self.load_document_editor(self.driver, self.doc)
        self.load_document_editor(self.driver2, self.doc)

        self.add_title(self.driver)

        document_input = self.driver.find_element_by_class_name(
            'ProseMirror-content'
        )

        # Total: 22
        self.driver.execute_script(
            'window.theEditor.pm.setTextSelection(23,23)')

        p1 = multiprocessing.Process(
            target=self.input_text,
            args=(document_input, self.TEST_TEXT)
        )
        p1.start()

        # Wait for the first processor to write some text
        self.wait_for_doc_size(self.driver2, 32)

        # without clicking on content the buttons will not work
        content = self.driver2.find_element_by_class_name(
            'ProseMirror-content'
        )
        content.click()

        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(23,28)')

        p2 = multiprocessing.Process(
            target=self.make_bold,
            args=(self.driver2,)
        )
        p2.start()
        p1.join()
        p2.join()

        self.assertEqual(
            5,
            len(self.get_boldtext(self.driver2))
        )

        self.assertEqual(
            len(self.get_boldtext(self.driver)),
            len(self.get_boldtext(self.driver2))
        )

    def make_italic(self, driver):
        button = driver.find_element_by_id('button-italic')
        button.click()

    def get_italictext(self, driver):
        itext = driver.find_element_by_xpath(
            '//*[contains(@class, "article-body")]/p/em')
        return itext.text

    def test_select_and_italic(self):
        """
        Test typing in collaborative mode with one user typing and
        another user italic some part of the text in two different threads.
        """
        self.load_document_editor(self.driver, self.doc)
        self.load_document_editor(self.driver2, self.doc)

        self.add_title(self.driver)

        document_input = self.driver.find_element_by_class_name(
            'ProseMirror-content'
        )

        # Total: 23
        self.driver.execute_script(
            'window.theEditor.pm.setTextSelection(23,23)')

        p1 = multiprocessing.Process(
            target=self.input_text,
            args=(document_input, self.TEST_TEXT)
        )
        p1.start()

        # Wait for the first processor to write some text
        self.wait_for_doc_size(self.driver2, 32)

        # without clicking on content the buttons will not work
        content = self.driver2.find_element_by_class_name(
            'ProseMirror-content'
        )
        content.click()

        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(23,28)')

        p2 = multiprocessing.Process(
            target=self.make_italic,
            args=(self.driver2,)
        )
        p2.start()
        p1.join()
        p2.join()

        self.assertEqual(
            5,
            len(self.get_italictext(self.driver2))
        )

        self.assertEqual(
            len(self.get_italictext(self.driver)),
            len(self.get_italictext(self.driver2))
        )

    def make_numberedlist(self, driver):
        button = driver.find_element_by_id('button-ol')
        button.click()

    def get_numberedlist(self, driver):
        numberedTags = driver.find_elements_by_xpath(
            '//*[contains(@class, "article-body")]//ol//li')
        return numberedTags

    def test_numberedlist(self):
        """
            Test typing in collaborative mode with one user typing and
            another user use numbered list button in two different threads.
            """
        self.load_document_editor(self.driver, self.doc)
        self.load_document_editor(self.driver2, self.doc)
        self.add_title(self.driver)

        document_input = self.driver.find_element_by_class_name(
            'ProseMirror-content'
        )

        # Total: 23
        self.driver.execute_script(
            'window.theEditor.pm.setTextSelection(23,23)')

        p1 = multiprocessing.Process(
            target=self.input_text,
            args=(document_input, self.MULTILINE_TEST_TEXT)
        )
        p1.start()

        # Wait for the first processor to write some text
        self.wait_for_doc_size(self.driver2, 30)

        # without clicking on content the buttons will not work
        content = self.driver2.find_element_by_class_name(
            'ProseMirror-content'
        )
        content.click()

        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(23,23)')

        p2 = multiprocessing.Process(
            target=self.make_numberedlist,
            args=(self.driver2,)
        )
        p2.start()
        p2.join()

        # Wait for the first processor to write some text and go to next line
        self.wait_for_doc_size(self.driver2, 47)

        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(41,41)')

        p2 = multiprocessing.Process(
            target=self.make_numberedlist,
            args=(self.driver2,)
        )
        p2.start()

        p1.join()
        p2.join()

        self.assertEqual(
            2,
            len(self.get_numberedlist(self.driver2))
        )

        self.assertEqual(
            len(self.get_numberedlist(self.driver)),
            len(self.get_numberedlist(self.driver2))
        )

    def make_bulletlist(self, driver):
        button = driver.find_element_by_id('button-ul')
        button.click()

    def get_bulletlist(self, driver):
        bulletTags = driver.find_elements_by_xpath(
            '//*[contains(@class, "article-body")]//ul//li')
        return bulletTags

    def test_bulletlist(self):
        """
            Test typing in collaborative mode with one user typing and
            another user use bullet list button in two different threads.
            """
        self.load_document_editor(self.driver, self.doc)
        self.load_document_editor(self.driver2, self.doc)

        self.add_title(self.driver)

        document_input = self.driver.find_element_by_class_name(
            'ProseMirror-content'
        )

        # Total: 23
        self.driver.execute_script(
            'window.theEditor.pm.setTextSelection(23,23)')

        p1 = multiprocessing.Process(
            target=self.input_text,
            args=(document_input, self.MULTILINE_TEST_TEXT)
        )
        p1.start()

        # Wait for the first processor to write some text
        self.wait_for_doc_size(self.driver2, 30)

        # without clicking on content the buttons will not work
        content = self.driver2.find_element_by_class_name(
            'ProseMirror-content'
        )
        content.click()

        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(23,23)')

        p2 = multiprocessing.Process(
            target=self.make_bulletlist,
            args=(self.driver2,)
        )
        p2.start()
        p2.join()

        # Wait for the first processor to write enough text and go to next line
        self.wait_for_doc_size(self.driver2, 47)

        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(41,41)')

        p2 = multiprocessing.Process(
            target=self.make_bulletlist,
            args=(self.driver2,)
        )
        p2.start()

        p1.join()
        p2.join()

        self.assertEqual(
            2,
            len(self.get_bulletlist(self.driver2))
        )

        self.assertEqual(
            len(self.get_bulletlist(self.driver)),
            len(self.get_bulletlist(self.driver2))
        )

    def make_blockquote(self, driver):
        button = driver.find_element_by_id('button-blockquote')
        button.click()

    def get_blockquote(self, driver):
        blockquoteTags = driver.find_elements_by_xpath(
            '//*[contains(@class, "article-body")]/blockquote')
        return blockquoteTags

    def test_blockquote(self):
        """
            Test typing in collaborative mode with one user typing and
            another user use block qoute button in two different threads.
            """
        self.load_document_editor(self.driver, self.doc)
        self.load_document_editor(self.driver2, self.doc)

        self.add_title(self.driver)

        document_input = self.driver.find_element_by_class_name(
            'ProseMirror-content'
        )

        # Total: 22
        self.driver.execute_script(
            'window.theEditor.pm.setTextSelection(23,23)')

        p1 = multiprocessing.Process(
            target=self.input_text,
            args=(document_input, self.TEST_TEXT)
        )
        p1.start()

        # Wait for the first processor to write some text
        self.wait_for_doc_size(self.driver2, 25)

        # without clicking on content the buttons will not work
        content = self.driver2.find_element_by_class_name(
            'ProseMirror-content'
        )
        content.click()

        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(23,23)')

        p2 = multiprocessing.Process(
            target=self.make_blockquote,
            args=(self.driver2,)
        )
        p2.start()
        p2.join()
        p1.join()

        self.assertEqual(
            1,
            len(self.get_blockquote(self.driver2))
        )

        self.assertEqual(
            len(self.get_blockquote(self.driver)),
            len(self.get_blockquote(self.driver2))
        )

    def addlink(self, driver):
        button = driver.find_element_by_id('button-link')
        button.click()

        # wait to load popup
        linktitle = WebDriverWait(driver, self.wait_time).until(
            EC.presence_of_element_located((By.CLASS_NAME, "link-title"))
        )
        linktitle.click()
        self.input_text(linktitle, "Test link")

        link = driver.find_element_by_class_name('link')
        self.input_text(link, "example.com")

        driver.find_element_by_xpath(
            "/html/body/div[5]/div[3]/div/button[1]").click()

    def get_link(self, driver):
        atag = driver.find_element_by_xpath(
            '//*[contains(@class, "article-body")]/p/a')
        return atag.text

    def test_add_link(self):
        """
        Test typing in collaborative mode with one user typing and
        another user select some part of the text and add link
        in two different threads.
        """
        self.load_document_editor(self.driver, self.doc)
        self.load_document_editor(self.driver2, self.doc)

        self.add_title(self.driver)

        document_input = self.driver.find_element_by_class_name(
            'ProseMirror-content'
        )

        # Total: 23
        self.driver.execute_script(
            'window.theEditor.pm.setTextSelection(23,23)')

        p1 = multiprocessing.Process(
            target=self.input_text,
            args=(document_input, self.TEST_TEXT)
        )
        p1.start()

        # Wait for the first processor to write some text
        self.wait_for_doc_size(self.driver2, 32)

        # without clicking on content the buttons will not work
        content = self.driver2.find_element_by_class_name(
            'ProseMirror-content'
        )
        content.click()

        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(23,28)')

        p2 = multiprocessing.Process(
            target=self.addlink,
            args=(self.driver2,)
        )
        p2.start()
        p1.join()
        p2.join()

        self.assertEqual(
            5,
            len(self.get_link(self.driver2))
        )

        self.assertEqual(
            len(self.get_link(self.driver)),
            len(self.get_link(self.driver2))
        )

    def make_footnote(self, driver):
        button = driver.find_element_by_id('button-footnote')
        button.click()

        # wait for footnote to be created
        WebDriverWait(driver, self.wait_time).until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, "footnote-container")
            )
        )

        footnote_box = driver.find_element_by_id(
            'footnote-box-container')
        footnote_editor = footnote_box.find_element_by_class_name(
            'ProseMirror-content')
        footnote_editor.click()

        self.input_text(footnote_editor, "footnote Text")

    def get_footnote(self, driver):
        atag = driver.find_element_by_xpath(
            '//*[@id="footnote-box-container"]/div[2]/div/div[1]/p/span'
        )
        return atag.text

    def test_footnote(self):
        """
        Test typing in collaborative mode with one user typing and
        another user add a footnote in two different threads.
        """
        self.load_document_editor(self.driver, self.doc)
        self.load_document_editor(self.driver2, self.doc)

        self.add_title(self.driver)

        document_input = self.driver.find_element_by_class_name(
            'ProseMirror-content'
        )

        # Total: 22
        self.driver.execute_script(
            'window.theEditor.pm.setTextSelection(23,23)')

        p1 = multiprocessing.Process(
            target=self.input_text,
            args=(document_input, self.TEST_TEXT)
        )
        p1.start()

        # Wait for the first processor to write some text
        self.wait_for_doc_size(self.driver2, 32)

        # without clicking on content the buttons will not work
        content = self.driver2.find_element_by_class_name(
            'ProseMirror-content'
        )
        content.click()

        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(28,28)')

        p2 = multiprocessing.Process(
            target=self.make_footnote,
            args=(self.driver2,)
        )
        p2.start()
        p1.join()
        p2.join()

        self.wait_for_doc_sync(self.driver, self.driver2)

        self.assertEqual(
            13,
            len(self.get_footnote(self.driver2))
        )

        self.assertEqual(
            len(self.get_footnote(self.driver)),
            len(self.get_footnote(self.driver2))
        )

    def perform_delete_undo(self, driver):
        element = driver.find_element_by_class_name('ProseMirror-content')
        element.send_keys(Keys.BACKSPACE)

        button = driver.find_element_by_id('button-undo')
        button.click()

    def get_undo(self, driver):
        content = driver.find_element_by_class_name('article-body')

        return content.text

    def test_delete_undo(self):
        """
        Test typing in collaborative mode with one user typing and
        another user delete and undo some part of the text in two different
        threads.
        """
        self.load_document_editor(self.driver, self.doc)
        self.load_document_editor(self.driver2, self.doc)

        self.add_title(self.driver)

        document_input = self.driver.find_element_by_class_name(
            'ProseMirror-content'
        )

        # Total: 22
        self.driver.execute_script(
            'window.theEditor.pm.setTextSelection(23,23)')

        p1 = multiprocessing.Process(
            target=self.input_text,
            args=(document_input, self.TEST_TEXT)
        )
        p1.start()

        # Wait for the first processor to write some text
        self.wait_for_doc_size(self.driver2, 32)

        # without clicking on content the buttons will not work
        content = self.driver2.find_element_by_class_name(
            'ProseMirror-content'
        )
        content.click()

        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(23,28)')

        p2 = multiprocessing.Process(
            target=self.perform_delete_undo,
            args=(self.driver2,)
        )
        p2.start()
        p1.join()
        p2.join()

        self.assertEqual(
            self.TEST_TEXT,
            self.get_undo(self.driver2)
        )

        self.assertEqual(
            self.get_undo(self.driver),
            self.get_undo(self.driver2)
        )

    def make_mathequation(self, driver):
        button = driver.find_element_by_id('button-math')
        button.click()

        # wait to load popup
        insert_button = WebDriverWait(driver, self.wait_time).until(
            EC.presence_of_element_located((By.CLASS_NAME, "insert-math"))
        )
        insert_button.click()

    def get_mathequation(self, driver):
        math = driver.find_element_by_xpath(
            '//*[contains(@class, "article-body")]/p[1]/span[2]'
            # OR '//*[@class="equation"]'
        )

        return math.text

    def test_mathequation(self):
        """
        Test typing in collaborative mode with one user typing and
        another user insert math equation in middle of the text in two
        different threads.
        """
        self.load_document_editor(self.driver, self.doc)
        self.load_document_editor(self.driver2, self.doc)

        self.add_title(self.driver)

        document_input = self.driver.find_element_by_class_name(
            'ProseMirror-content'
        )

        # Total: 23
        self.driver.execute_script(
            'window.theEditor.pm.setTextSelection(23,23)')

        p1 = multiprocessing.Process(
            target=self.input_text,
            args=(document_input, self.TEST_TEXT)
        )
        p1.start()

        # Wait for the first processor to write some text
        self.wait_for_doc_size(self.driver2, 32)

        # without clicking on content the buttons will not work
        content = self.driver2.find_element_by_class_name(
            'ProseMirror-content'
        )
        content.click()

        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(28,28)')

        p2 = multiprocessing.Process(
            target=self.make_mathequation,
            args=(self.driver2,)
        )
        p2.start()
        p1.join()
        p2.join()

        self.assertEqual(
            55,
            len(self.get_mathequation(self.driver2))
        )

        self.assertEqual(
            len(self.get_mathequation(self.driver)),
            len(self.get_mathequation(self.driver2))
        )

    def add_comment(self, driver):
        button = driver.find_element_by_id('button-comment')
        button.click()

        textArea = WebDriverWait(driver, self.wait_time).until(
            EC.presence_of_element_located((By.CLASS_NAME, "commentText"))
        )
        textArea.click()

        self.input_text(textArea, "My comment")

        driver.find_element_by_class_name("submitComment").click()

    def get_comment(self, driver):
        comment = driver.find_element_by_class_name('comment-text-wrapper')

        return comment.text

    def test_comment(self):
        """
        Test typing in collaborative mode with one user typing and
        another user add some comment in middle of the text in two different
        threads.
        """
        self.load_document_editor(self.driver, self.doc)
        self.load_document_editor(self.driver2, self.doc)

        self.add_title(self.driver)

        document_input = self.driver.find_element_by_class_name(
            'ProseMirror-content'
        )

        # Total: 22
        self.driver.execute_script(
            'window.theEditor.pm.setTextSelection(23,23)')

        p1 = multiprocessing.Process(
            target=self.input_text,
            args=(document_input, self.TEST_TEXT)
        )
        p1.start()

        # Wait for the first processor to write some text
        self.wait_for_doc_size(self.driver2, 33)

        # without clicking on content the buttons will not work
        content = self.driver2.find_element_by_class_name(
            'ProseMirror-content'
        )
        content.click()

        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(23,28)')

        p2 = multiprocessing.Process(
            target=self.add_comment,
            args=(self.driver2,)
        )
        p2.start()
        p1.join()
        p2.join()

        self.wait_for_doc_sync(self.driver, self.driver2)

        self.assertEqual(
            10,
            len(self.get_comment(self.driver2))
        )

        self.assertEqual(
            len(self.get_comment(self.driver)),
            len(self.get_comment(self.driver2))
        )

    def add_figure(self, driver):
        button = driver.find_element_by_id('button-figure')
        button.click()

        caption = WebDriverWait(driver, self.wait_time).until(
            EC.presence_of_element_located((By.CLASS_NAME, "caption"))
        )

        self.input_text(caption, "My figure")

        # click on 'Insert image' button
        driver.find_element_by_id('insertFigureImage').click()

        upload_button = WebDriverWait(driver, self.wait_time).until(
            EC.presence_of_element_located((By.ID, 'selectImageUploadButton'))
        )

        upload_button.click()

        # image path
        imagePath = os.path.join(
            settings.PROJECT_PATH,
            'document/tests/uploads/image.png'
        )

        # inorder to select the image we send the image path in the
        # LOCAL MACHINE to the input tag
        upload_image_url = WebDriverWait(driver, self.wait_time).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="uploadimage"]/form/div[1]/input[2]')
            )
        )
        upload_image_url.send_keys(imagePath)

        # click on 'Upload' button
        driver.find_element_by_xpath(
            '//*[contains(@class, "ui-button") and text()="Upload"]').click()

        # click on 'Use image' button
        WebDriverWait(driver, self.wait_time).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '#select_imagelist tr.checked')
            )
        )

        driver.find_element_by_id('selectImageSelectionButton').click()

        # click on 'Insert' button
        driver.find_element_by_xpath(
            '/html/body/div[5]/div[3]/div/button[1]').click()

    def get_image(self, driver):
        figure = driver.find_element_by_xpath(
            '//*[contains(@class, "article-body")]/figure'
        )
        image = figure.find_elements_by_tag_name('img')

        return image

    def get_caption(self, driver):
        caption = driver.find_element_by_xpath(
            '//*[contains(@class, "article-body")]/figure/figcaption/span[2]'
        )

        return caption.text

    def test_insertFigure(self):
        """
        Test typing in collaborative mode with one user typing and
        another user insert figure middle of the text in two different threads.
        """
        self.load_document_editor(self.driver, self.doc)
        self.load_document_editor(self.driver2, self.doc)

        self.add_title(self.driver)

        document_input = self.driver.find_element_by_class_name(
            'ProseMirror-content'
        )

        # Total: 23
        self.driver.execute_script(
            'window.theEditor.pm.setTextSelection(23,23)')

        p1 = multiprocessing.Process(
            target=self.input_text,
            args=(document_input, self.TEST_TEXT)
        )
        p1.start()

        # Wait for the first processor to write some text
        self.wait_for_doc_size(self.driver2, 32)

        # without clicking on content the buttons will not work
        content = self.driver2.find_element_by_class_name(
            'ProseMirror-content'
        )
        content.click()

        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(28,28)')

        p2 = multiprocessing.Process(
            target=self.add_figure,
            args=(self.driver2,)
        )
        p2.start()
        p1.join()
        p2.join()

        self.assertEqual(
            1,
            len(self.get_image(self.driver2))
        )

        self.assertEqual(
            len(self.get_image(self.driver)),
            len(self.get_image(self.driver2))
        )

        self.assertEqual(
            9,
            len(self.get_caption(self.driver2))
        )
        self.assertEqual(
            len(self.get_caption(self.driver)),
            len(self.get_caption(self.driver2))
        )

    def add_citation(self, driver):
        button = driver.find_element_by_id('button-cite')
        button.click()

        # click on 'Register new source' button
        register_new_source = WebDriverWait(driver, self.wait_time).until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, 'register-new-bib-source')
            )
        )
        register_new_source.click()

        # select source
        WebDriverWait(driver, self.wait_time).until(
            EC.presence_of_element_located((By.ID, 'select-bibtype'))
        )

        # click on article
        Select(
            driver.find_element_by_id("select-bibtype")
        ).select_by_visible_text("Article")

        # fill the values
        title_of_publication = driver.find_element_by_css_selector(
            '.journaltitle .ProseMirror-content'
        )
        title_of_publication.click()
        title_of_publication.send_keys("My publication title")

        title = driver.find_element_by_css_selector(
            '.title .ProseMirror-content')
        title.click()
        title.send_keys("My title")

        author_firstName = driver.find_element_by_css_selector(
            '.author .given .ProseMirror-content')
        author_firstName.click()
        author_firstName.send_keys("John")

        author_lastName = driver.find_element_by_css_selector(
            '.family .ProseMirror-content')
        author_lastName.click()
        author_lastName.send_keys("Doe")

        publication_date = driver.find_element_by_css_selector(
            '.date .date'
        )
        publication_date.click()
        publication_date.send_keys("2012")

        # click on Submit button
        driver.find_element_by_xpath(
            '//*[contains(@class, "ui-button") and text()="Submit"]').click()

        # Wait for source to be listed
        WebDriverWait(driver, self.wait_time).until(
            EC.element_to_be_clickable(
                (
                    By.CSS_SELECTOR,
                    '#selected-cite-source-table .selected-source'
                )
            )
        )

        # click on Insert button
        driver.find_element_by_css_selector('.insert-citation').click()

    def get_citation_within_text(self, driver):
        cite_within_doc = driver.find_element_by_xpath(
            '//*[contains(@class, "article-body")]/p[1]/span[2]'
        )
        return cite_within_doc.text

    def get_citation_bib(self, driver):
        cite_bib = driver.find_element_by_class_name('article-bibliography')
        return cite_bib.text

    def test_citation(self):
        """
        Test typing in collaborative mode with one user typing and
        another user add cite in two different threads.
        """
        self.load_document_editor(self.driver, self.doc)
        self.load_document_editor(self.driver2, self.doc)

        self.add_title(self.driver)

        document_input = self.driver.find_element_by_class_name(
            'ProseMirror-content'
        )

        # Total: 22
        self.driver.execute_script(
            'window.theEditor.pm.setTextSelection(23,23)')

        p1 = multiprocessing.Process(
            target=self.input_text,
            args=(document_input, self.TEST_TEXT)
        )
        p1.start()

        # Wait for the first processor to write some text
        self.wait_for_doc_size(self.driver2, 32)

        # without clicking on content the buttons will not work
        content = self.driver2.find_element_by_class_name(
            'ProseMirror-content'
        )
        content.click()

        self.driver2.execute_script(
            'window.theEditor.pm.setTextSelection(28,28)')

        p2 = multiprocessing.Process(
            target=self.add_citation,
            args=(self.driver2,)
        )
        p2.start()
        p1.join()
        p2.join()

        self.wait_for_doc_sync(self.driver, self.driver2)

        self.assertEqual(
            10,
            len(self.get_citation_within_text(self.driver2))
        )

        self.assertEqual(
            len(self.get_citation_within_text(self.driver)),
            len(self.get_citation_within_text(self.driver2))
        )

        self.assertEqual(
            47,
            len(self.get_citation_bib(self.driver))
        )

        self.assertEqual(
            len(self.get_citation_bib(self.driver)),
            len(self.get_citation_bib(self.driver2))
        )
