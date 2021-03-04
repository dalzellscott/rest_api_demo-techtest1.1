import logging
import random
import time
import sys
import unittest
from multiprocessing.pool import ThreadPool

import api

api = api.Api.instance()
logging.getLogger().setLevel(logging.INFO)


def _calling_method():
    """prints the name of the method that calls it"""
    raw = sys._getframe(1).f_code.co_name
    logging.info(f"Running: <{raw}>")


class TestCategories(unittest.TestCase):
    def setUp(self):
        api._clean_db()

    def test_get_categories_successful_200(self):
        _calling_method()
        response = api.get_categories()
        self.assertEqual(200, response.status_code)

    def test_get_categories_values(self):
        _calling_method()
        response = api.get_categories()
        categories = response.json()
        expected_values = [{"id": 1, "name": "Sci-Fi"},
                           {"id": 2, "name": "Politics"},
                           {"id": 3, "name": "Tech"}]

        for category in categories:
            e_value = expected_values[category.get("id") - 1]
            self.assertEqual(e_value.get("name"), category.get("name"), f"Error with {e_value}")

    def test_create_category_successful_201(self):
        _calling_method()

        categories_before = api._no_of_categories()

        response = api.create_category(name="Test_category", id=4)
        self.assertEqual(201, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 201")

        categories_after = api._no_of_categories()
        self.assertEqual(categories_before + 1, categories_after, "Category not created")

    def test_create_category_successful_201_name(self):
        _calling_method()
        categories_before = api._no_of_categories()

        response = api.create_category(name="Test_category", id=4)
        self.assertEqual(201, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 201")

        categories_after = api._no_of_categories()
        self.assertEqual(categories_before + 1, categories_after, "Category not created")
        self.assertTrue(api._verify_category(id=4, name="Test_category"), "Category created incorrectly")

    def test_create_category_duplicate_id_500(self):
        _calling_method()
        categories_before = api._no_of_categories()
        response = api.create_category(name="Test_category_1", id=4)
        self.assertEqual(201, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 201")

        categories_after = api._no_of_categories()

        self.assertEqual(categories_after, categories_before + 1, "Category not created")

        # Second insert of ID
        response = api.create_category(name="Test_category_2", id=4)
        self.assertEqual(500, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 500")

        categories_after = api._no_of_categories()
        self.assertEqual(categories_before + 1, categories_after, "Category with duplicate ID created")

    def test_create_category_10(self):
        _calling_method()
        expected = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]

        for i in range(10):
            api.create_category(name=f"Test_category_{i}")

        category_ids = api._get_category_ids()

        self.assertEqual(expected, category_ids, "Category Ids miss match")

    def test_delete_category_success_204(self):
        _calling_method()
        api.create_category(name="success_204", id=4)
        categories_before = api._no_of_categories()
        response = api.delete_category(4)
        self.assertEqual(204, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 204")
        categories_after = api._no_of_categories()
        self.assertEqual(categories_before - 1, categories_after, "Category not deleted")

    def test_delete_of_multiple_categories(self):
        _calling_method()
        expected = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
        for index in range(10):
            api.create_category(name=f"Test_category_{index}")

        category_ids = api._get_category_ids()
        self.assertEqual(expected, category_ids, "Category Ids miss match")

        deleted = [4, 6, 8, 10, 12]
        for index in deleted:
            api.delete_category(index)

        expected_after = set(expected) - set(deleted)
        category_ids = set(api._get_category_ids())
        self.assertEqual(expected_after, category_ids, "Category Ids miss match")

    def test_delete_of_multiple_categories_then_adding_new_categories(self):
        _calling_method()
        # Create categories
        expected = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
        for index in range(10):
            api.create_category(name=f"Test_category_{index}")

        category_ids = api._get_category_ids()
        self.assertEqual(expected, category_ids, "Category Ids miss match")

        # Delete several Categories
        deleted = [4, 6, 8, 10, 12]
        for index in deleted:
            api.delete_category(index)

        expected_after = set(expected) - set(deleted)
        category_ids = set(api._get_category_ids())
        self.assertEqual(expected_after, category_ids, "Category Ids miss match")

        # Add Categories in middle of ID range
        added = [6, 10]
        for index in added:
            api.create_category(name=f"Test_category_{index}", id=index)

        expected_after_add = set(list(expected_after) + list(added))
        category_ids = set(api._get_category_ids())
        self.assertEqual(expected_after_add, category_ids, "Category Ids miss match")

    def test_delete_category_not_found_404(self):
        _calling_method()
        categories_before = api._no_of_categories()
        response = api.delete_category(4)
        self.assertEqual(404, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 404")
        categories_after = api._no_of_categories()
        self.assertEqual(categories_before, categories_after, "Category deleted")

    def test_delete_category_in_use_not_deleted_409(self):
        _calling_method()

        # Functions to soak category with updates to prevent delete
        def _update_category(category_id, no=1):
            for index in range(no):
                time.sleep(random.randint(1, 25)/1000)
                logging.info(f"update: category {category_id}")
                api.update_category(id=category_id, name=f"Update_category_name_{category_id}")

        def _post_lots(category_id, no=1):
            for index in range(no):
                time.sleep(random.randint(1, 25) / 1000)
                logging.info(f"Post {index}")
                api.create_post(title=f"post {index}", body=f"This is a test body {index}", category_id=category_id)

        for i in range(50):
            api.create_category(name=f"Test_category", id=4)
            pool = ThreadPool(processes=5)

            pool.apply_async(_post_lots, args=[4, 2])
            pool.apply_async(_update_category, args=[4, 2])

            _response = pool.apply_async(api.delete_category, args=[4])

            pool.apply_async(_post_lots, args=[4, 2])
            pool.apply_async(_update_category, args=[4, 2])

            pool.close()
            pool.join()
            response = _response._value
            if response is not None:
                if response.status_code != 204:
                    break

        self.assertEqual(409, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 409")

    def test_get_category_found_200(self):
        _calling_method()
        api.create_category(name="Test_category", id=4)
        response = api.get_category(4)
        self.assertEqual(200, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 200")

    def test_get_category_not_found_404(self):
        _calling_method()
        response = api.get_category(4)
        self.assertEqual(404, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 404")

    def test_get_category_values_4(self):
        _calling_method()
        api.create_category(name="Test_category", id=4)
        api._verify_category(id=4)
        self.assertTrue(api._verify_category(id=4), f"Category has incorrect Id returned")

    def test_get_category_value_10(self):
        _calling_method()
        for index in range(4, 10):
            api.create_category(name=f"Test_category_{index}")
            self.assertTrue(api._verify_category(id=index), f"Category has incorrect Id returned")

    def test_update_category_successful_204(self):
        _calling_method()
        api.create_category(name="Test_category")
        response = api.update_category(id=4, name="Update_category_name")
        self.assertEqual(204, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 204")
        self.assertTrue(api._verify_category(id=4, name="Update_category_name"), "Category was not updated correctly")

    def test_update_category_id_fail_404(self):
        _calling_method()
        api.create_category(name="Test_category", id=4)
        response = api.update_category(id=5, name="Update_category_name")
        self.assertEqual(404, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 404")


class TestPosts(unittest.TestCase):
    def setUp(self):
        api._clean_db()

    def test_get_posts_success_200(self):
        _calling_method()
        kwargs = {"page": 1,
                  "b": True,
                  "per_page": 10}
        response = api.get_posts(**kwargs)
        self.assertEqual(200, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 200")

    def test_get_posts_fail_400(self):
        _calling_method()
        kwargs = {"page": 1,
                  "per_page": 3}
        response = api.get_posts(**kwargs)
        self.assertEqual(400, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 400")

    def test_get_posts_bool_arg_does_something(self):
        _calling_method()
        kwargs = {"page": 1,
                  "b": True,
                  "per_page": 10}
        response_true = api.get_posts(**kwargs)
        self.assertEqual(200, response_true.status_code,
                         f"Incorrect Response Code return : {response_true.status_code} but expected 200")

        kwargs = {"page": 1,
                  "b": False,
                  "per_page": 10}
        response_false = api.get_posts(**kwargs)
        self.assertEqual(200, response_false.status_code,
                         f"Incorrect Response Code return : {response_false.status_code} but expected 200")

        posts_true = response_true.json()
        posts_false = response_false.json()

        self.assertNotEqual(posts_true, posts_false, "Bool operator on Get /blog/posts/ does nothing")

    def test_get_posts_per_page_2(self):
        _calling_method()
        expected = {"items": 2,
                    "page": 1,
                    "pages": 3,
                    "total": 5}

        kwargs = {"page": 1,
                  "per_page": 2}

        self.assertTrue(api._verify_posts(expected=expected, **kwargs))

    def test_get_posts_per_page_10(self):
        _calling_method()
        expected = {"items": 10,
                    "page": 1,
                    "pages": 2,
                    "total": 15}

        kwargs = {"page": 1,
                  "per_page": 10}

        api.create_category(name="Test_category", id=4)

        for index in range(expected.get("items")):
            logging.info(f"Post {index}")
            api.create_post(title=f"post {index}", body=f"This is a test body {index}", category_id=4)

        self.assertTrue(api._verify_posts(expected=expected, **kwargs))

    def test_get_posts_per_page_20(self):
        _calling_method()

        expected = {"items": 20,
                    "page": 1,
                    "pages": 2,
                    "total": 25}

        kwargs = {"page": 1,
                  "per_page": 20}

        api.create_category(name="Test_category", id=4)

        for index in range(expected.get("items")):
            logging.info(f"Post {index}")
            api.create_post(title=f"post {index}", body=f"This is a test body {index}", category_id=4)

        self.assertTrue(api._verify_posts(expected=expected, **kwargs))

    def test_get_posts_per_page_30(self):
        _calling_method()

        expected = {"items": 30,
                    "page": 1,
                    "pages": 2,
                    "total": 35}

        kwargs = {"page": 1,
                  "per_page": 30}

        api.create_category(name="Test_category", id=4)

        for index in range(expected.get("items")):
            logging.info(f"Post {index}")
            api.create_post(title=f"post {index}", body=f"This is a test body {index}", category_id=4)

        self.assertTrue(api._verify_posts(expected=expected, **kwargs))

    def test_get_posts_per_page_40(self):
        _calling_method()

        expected = {"items": 40,
                    "page": 1,
                    "pages": 2,
                    "total": 45}

        kwargs = {"page": 1,
                  "per_page": 40}

        api.create_category(name="Test_category", id=4)

        for index in range(expected.get("items")):
            logging.info(f"Post {index}")
            api.create_post(title=f"post {index}", body=f"This is a test body {index}", category_id=4)

        self.assertTrue(api._verify_posts(expected=expected, **kwargs))

    def test_get_posts_per_page_50(self):
        _calling_method()
        expected = {"items": 50,
                    "page": 1,
                    "pages": 2,
                    "total": 55}

        kwargs = {"page": 1,
                  "per_page": 50}

        api.create_category(name="Test_category", id=4)

        for index in range(expected.get("items")):
            logging.info(f"Post {index}")
            api.create_post(title=f"post {index}", body=f"This is a test body {index}", category_id=4)

        self.assertTrue(api._verify_posts(expected=expected, **kwargs))

    def test_get_posts_per_page_non_valid_value_used(self):
        _calling_method()
        expected = {"message": "Input payload validation failed",
                    "per_page": "Results per page 3 is not a valid choice"}

        kwargs = {"page": 1,
                  "per_page": 3}

        self.assertTrue(api._verify_posts(expected=expected, **kwargs))

    def test_get_posts_page_2(self):
        _calling_method()
        expected = {"items": 2,
                    "page": 2,
                    "pages": 3,
                    "total": 5}

        kwargs = {"page": 2,
                  "per_page": 2}

        self.assertTrue(api._verify_posts(expected=expected, **kwargs),
                        "Not displaying posts on page 2 of 3 as expected")

    def test_create_post_success_200(self):
        _calling_method()
        kwargs = {"title": "This is the title",
                  "body": "This is the body of text",
                  "category_id": 4
                  }

        api.create_category(name="Test_category", id=4)
        response = api.create_post(**kwargs)
        self.assertEqual(200, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 200")

    def test_create_post_required_category_id_404(self):
        _calling_method()
        kwargs = {"title": "This is the title",
                  "body": "This is the body of text",
                  }

        api.create_category(name="Test_category", id=4)
        response = api.create_post(**kwargs)
        self.assertEqual(404, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 404")

    def test_get_post_success_200(self):
        _calling_method()
        response = api.get_post(id=1)
        self.assertEqual(200, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 200")

    def test_get_post_fail_404(self):
        _calling_method()
        response = api.get_post(id=99)
        self.assertEqual(404, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 404")

    def test_get_post_verify_contents_id_1(self):
        _calling_method()
        kwargs = {"title": "The Road to Extinction",
                  "body": "The drought had lasted now for ten million years, and the reign of the terrible lizards had long since ended. Here on the Equator, in the continent which would one day be known as Africa, the battle for existence had reached a new climax of ferocity, and the victor was not yet in sight. In this barren and desiccated land, only the small or the swift or the fierce could flourish, or even hope to survive.",
                  "category_id": 1
                  }

        response = api.get_category(id=1)
        category = response.json()

        expected = {"title": kwargs.get("title"),
                    "body": kwargs.get("body"),
                    "category": category.get("name"),
                    "category_id": kwargs.get("category_id"),
                    "id": 1
                    }

        self.assertTrue(api._verify_post(expected, id=expected.get("id")))

    def test_get_post_verify_contents_id_5(self):
        _calling_method()
        kwargs = {"title": "Encounter in the Dawn",
                  "body": "As he led the tribe down to the river in the dim light of dawn, Moon-Watcher paused uncertainly at a familiar spot. Something, he knew, was missing; but what it was, he could not remember. He wasted no mental effort on the problem, for this morning he had more important matters on his mind.",
                  "category_id": 1,
                  "id": 5
                  }

        api.create_category(name="Test_category", id=4)

        response = api.get_category(id=1)
        category = response.json()

        expected = {"title": kwargs.get("title"),
                    "body": kwargs.get("body"),
                    "category": category.get("name"),
                    "category_id": kwargs.get("category_id"),
                    "id": kwargs.get("id"),
                    }

        new_post = {"title": "Test Title",
                    "body": "Test body",
                    "category_id": 4
                    }

        api.create_post(**new_post)
        self.assertTrue(api._verify_post(expected, id=expected.get("id")))

    def test_delete_post_success_204(self):
        _calling_method()
        new_post = {"title": "Test Title",
                    "body": "Test body",
                    "category_id": 4
                    }
        api.create_category(name="Test_category", id=4)
        api.create_post(**new_post)

        response = api.delete_post(id=6)
        self.assertEqual(204, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 204")

    def test_delete_post_fail_404(self):
        _calling_method()
        response = api.delete_post(id=6)
        self.assertEqual(404, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 404")

    def test_update_post_success_204(self):
        _calling_method()
        api.create_category(name="Test_category", id=4)
        new_post = {"title": "Test Title",
                    "body": "Test body",
                    "category_id": 4
                    }

        update_post = {"id": 6,
                       "title": "Test Title updated",
                       "body": "Test body updated",
                       "category_id": 4
                       }

        api.create_post(**new_post)

        response = api.update_post(**update_post)
        self.assertEqual(204, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 204")

    def test_update_post_fail_404(self):
        _calling_method()
        api.create_category(name="Test_category", id=4)
        new_post = {"title": "Test Title",
                    "body": "Test body",
                    "category_id": 4
                    }

        update_post = {"id": 99,
                       "title": "Test Title updated",
                       "body": "Test body updated",
                       "category_id": 4
                       }

        api.create_post(**new_post)

        response = api.update_post(**update_post)
        self.assertEqual(404, response.status_code,
                         f"Incorrect Response Code return : {response.status_code} but expected 404")

    def test_update_post_verify_content(self):
        _calling_method()
        api.create_category(name="Test_category", id=4)
        response = api.get_category(id=4)
        category = response.json()

        new_post = {"title": "Test Title",
                    "body": "Test body",
                    "category_id": 4
                    }

        update_post = {"id": 6,
                       "title": "Test Title updated",
                       "body": "Test body updated",
                       "category": category.get("name"),
                       "category_id": 4
                       }

        api.create_post(**new_post)
        api.update_post(**update_post)

        expected = {"title": update_post.get("title"),
                    "body": update_post.get("body"),
                    "category": category.get("name"),
                    "category_id": update_post.get("category_id"),
                    "id": 5  # to deal with know issue of get_post returning id+1 when selecting id=5 or above
                    }

        self.assertTrue(api._verify_post(expected, id=expected.get("id"), exclude_id=True))


if __name__ == "__main__":
    unittest.main()
