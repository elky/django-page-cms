# -*- coding: utf-8 -*-
"""Django page CMS test suite module"""
from django.template import Template, RequestContext, Context
from django.template import RequestContext, TemplateDoesNotExist
from django.template import loader
import django

from gerbi.models import Page, Content
from gerbi.tests.testcase import TestCase

class RegressionTestCase(TestCase):
    """Django page CMS test suite class"""

    def test_calculated_status_bug(self):
        """
        Test the issue 100
        http://code.google.com/p/django-page-cms/issues/detail?id=100
        """
        self.set_setting("GERBI_SHOW_START_DATE", True)
        c = self.get_admin_client()
        c.login(username= 'batiste', password='b')
        page_data = self.get_new_page_data()
        page_data['slug'] = 'page1'
        # create a page for the example otherwise you will get a Http404 error
        response = c.post('/admin/gerbi/page/add/', page_data)
        page1 = Content.objects.get_content_slug_by_slug('page1').page

        page1.status = Page.DRAFT
        page1.save()

        self.assertEqual(page1.calculated_status, Page.DRAFT)

    def test_slug_bug(self):
        """
        Test the issue 97
        http://code.google.com/p/django-page-cms/issues/detail?id=97
        """
        c = self.get_admin_client()
        c.login(username= 'batiste', password='b')
        page_data = self.get_new_page_data()
        page_data['slug'] = 'page1'
        # create a page for the example otherwise you will get a Http404 error
        response = c.post('/admin/gerbi/page/add/', page_data)

        response = c.get('/gerbi/page1/')
        self.assertEqual(response.status_code, 200)

        try:
            response = c.get(self.get_page_url('toto/page1/'))
        except TemplateDoesNotExist, e:
            if e.args != ('404.html',):
                raise

    def test_bug_152(self):
        """Test bug 152
        http://code.google.com/p/django-page-cms/issues/detail?id=152"""
        from gerbi.utils import get_placeholders
        self.assertEqual(
            str(get_placeholders('gerbi/tests/test1.html')),
            "[<Placeholder Node: body>]"
        )

    def test_bug_162(self):
        """Test bug 162
        http://code.google.com/p/django-page-cms/issues/detail?id=162"""
        c = self.get_admin_client()
        c.login(username= 'batiste', password='b')
        page_data = self.get_new_page_data()
        page_data['title'] = 'test-162-title'
        page_data['slug'] = 'test-162-slug'
        response = c.post('/admin/gerbi/page/add/', page_data)

        self.assertRedirects(response, '/admin/gerbi/page/')

        from gerbi.utils import get_request_mock
        request = get_request_mock()
        temp = loader.get_template('gerbi/tests/test2.html')
        render = temp.render(RequestContext(request, {}))
        self.assertTrue('test-162-slug' in render)

    def test_bug_172(self):
        """Test bug 167
        http://code.google.com/p/django-page-cms/issues/detail?id=172"""
        c = self.get_admin_client()
        c.login(username= 'batiste', password='b')
        page_data = self.get_new_page_data()
        page_data['title'] = 'title-en-us'
        page_data['slug'] = 'slug'
        response = c.post('/admin/gerbi/page/add/', page_data)
        page = Content.objects.get_content_slug_by_slug('slug').page
        Content(page=page, type='title', language='fr-ch',
            body="title-fr-ch").save()

        page.invalidate()

        from gerbi.utils import get_request_mock
        request = get_request_mock()
        temp = loader.get_template('gerbi/tests/test3.html')
        render = temp.render(RequestContext(request, {'page':page}))
        self.assertTrue('title-en-us' in render)

        render = temp.render(RequestContext(
            request,
            {'page': page, 'lang': 'fr-ch'}
        ))
        self.assertTrue('title-fr-ch' in render)


    def test_page_id_in_template(self):
        """Get a page in the templates via the page id."""
        page = self.create_new_page()
        from gerbi.utils import get_request_mock
        request = get_request_mock()
        temp = loader.get_template('gerbi/tests/test4.html')
        render = temp.render(RequestContext(request, {}))
        self.assertTrue(page.title() in render)

    def test_bug_178(self):
        """http://code.google.com/p/django-page-cms/issues/detail?id=178"""
        from gerbi.utils import get_request_mock
        request = get_request_mock()
        temp = loader.get_template('gerbi/tests/test5.html')
        render = temp.render(RequestContext(request, {'page': None}))

    def test_language_fallback_bug(self):
        """Language fallback doesn't work properly."""
        page = self.create_new_page()

        c = Content(page=page, type='new_type', body='toto', language='en-us')
        c.save()

        page.invalidate()

        self.assertEqual(
            Content.objects.get_content(page, 'en-us', 'new_type'),
            'toto'
        )
        self.assertEqual(
            Content.objects.get_content(page, 'fr-ch', 'new_type'),
            ''
        )
        self.assertEqual(
            Content.objects.get_content(page, 'fr-ch', 'new_type', True),
            'toto'
        )

    def test_bug_156(self):
        c = self.get_admin_client()
        c.login(username= 'batiste', password='b')
        page_data = self.get_new_page_data()
        page_data['slug'] = 'page1'
        page_data['title'] = 'title &amp;'
        response = c.post('/admin/gerbi/page/add/', page_data)
        page1 = Content.objects.get_content_slug_by_slug('page1').page
        page1.invalidate()
        c = Content.objects.get_content(page1, 'en-us', 'title')
        self.assertEqual(c, page_data['title'])

    def test_bug_181(self):
        c = self.get_admin_client()
        c.login(username= 'batiste', password='b')
        page_data = self.get_new_page_data(draft=True)
        page_data['slug'] = 'page1'

        # create a draft page and ensure we can view it
        response = c.post('/admin/gerbi/page/add/', page_data)
        response = c.get(self.get_page_url('page1/'))
        self.assertEqual(response.status_code, 200)

        # logout and we should get a 404
        c.logout()
        def func():
            return c.get(self.get_page_url('page1/'))
        self.assert404(func)

        # login as a non staff user and we should get a 404
        c.login(username= 'nonstaff', password='b')
        def func():
            return c.get(self.get_page_url('page1/'))
        self.assert404(func)


    def test_urls_in_templates(self):
        """Test different ways of displaying urls in templates."""
        page = self.create_new_page()
        from gerbi.http import get_request_mock
        request = get_request_mock()
        temp = loader.get_template('gerbi/tests/test7.html')
        temp = loader.get_template('gerbi/tests/test6.html')
        render = temp.render(RequestContext(request, {'gerbi_current_page':page}))

        self.assertTrue('t1_'+page.get_url_path() in render)
        self.assertTrue('t2_'+page.get_url_path() in render)
        self.assertTrue('t3_'+page.get_url_path() in render)
        self.assertTrue('t4_'+page.slug() in render)
        self.assertTrue('t5_'+page.slug() in render)


    def test_placeholder_cache_bug(self):
        """There was an bad bug caused when the page cache was filled
        the first time."""
        from gerbi.placeholders import PlaceholderNode
        page = self.new_page()
        placeholder = PlaceholderNode('test', page=page)
        placeholder.save(page, 'fr-ch', 'fr', True)
        placeholder.save(page, 'en-us', 'en', True)
        page.invalidate()
        self.assertEqual(
            Content.objects.get_content(page, 'fr-ch', 'test'),
            'fr'
        )

    def test_pages_dynamic_tree_menu_bug(self):
        """
        Test a bug with the dynamic tree template tag doesn't occur anymore.
        http://code.google.com/p/django-page-cms/issues/detail?id=209
        """
        page = self.new_page()
        context = Context({'gerbi_current_page': page, 'lang':'en-us'})

        pl1 = """{% load gerbi_tags %}{% gerbi_dynamic_tree_menu "wrong-slug" %}"""
        template = loader.get_template_from_string(pl1)
        self.assertEqual(template.render(context), u'\n')

    def test_placeholder_bug(self):
        """Test placeholder with django template inheritance works prepoerly.
        http://code.google.com/p/django-page-cms/issues/detail?id=210
        """
        p1 = self.new_page(content={'slug':'test', 'one':'one', 'two': 'two'})
        template = django.template.loader.get_template('gerbi/tests/extends.html')
        context = Context({'gerbi_current_page': p1, 'lang':'en-us'})
        renderer = template.render(context)
        self.assertTrue('one' in renderer)
        self.assertTrue('two' in renderer)

        from gerbi.utils import get_placeholders
        self.assertEqual(
            str(get_placeholders('gerbi/tests/extends.html')),
            '[<Placeholder Node: one>, <Placeholder Node: two>]')
