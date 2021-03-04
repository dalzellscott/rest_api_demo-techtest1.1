"""
Helper functions for testing Rest API
"""

import json
import requests
import time
import logging
from multiprocessing.pool import ThreadPool


class Singleton:
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.

    The decorated class can define one `__init__` function that
    takes only the `self` argument. Also, the decorated class cannot be
    inherited from. Other than that, there are no restrictions that apply
    to the decorated class.

    To get the singleton instance, use the `instance` method. Trying
    to use `__call__` will result in a `TypeError` being raised.

    """

    def __init__(self, decorated):
        self._decorated = decorated

    def instance(self, *args, **kwargs):
        """
        Returns the singleton instance. Upon its first call, it creates a
        new instance of the decorated class and calls its `__init__` method.
        On all subsequent calls, the already created instance is returned.
        """
        self._instance = self._decorated(*args, **kwargs)
        return self._instance

    def __call__(self):
        raise TypeError("Singletons must be accessed through `instance()`.")

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)


@Singleton
class Api:
    def __init__(self):
        self.base = "http://localhost:8888/api/"
        self.categories = f"{self.base}blog/categories/"
        self.posts = f"{self.base}blog/posts/"
        self.archive = f"{self.base}blog/posts/archive/"
        self.headers = {'Content-Type': "application/json"}

    def _json_data(self, **kwargs):
        """
        Helper method to only return json data for args which are not None
        :param kwargs: <dict> : API args to be converted to json
        :return: <bytes> : json data
        """
        data = {}
        for kw in kwargs:
            value = kwargs.get(kw)
            if value is not None:
                data[kw] = value

        json_data = json.dumps(data).encode("utf-8")
        return json_data

    def _no_of_categories(self):
        """
        returns the number of categories
        :return: <int>
        """
        response = self.get_categories()
        categories = response.json()

        logging.info(f"No of Categories: {len(categories)}")
        return len(categories)

    def _get_category_ids(self):
        """
        returns a list of all the category id in db
        :return: <list>
        """
        results = []
        response = self.get_categories()
        categories = response.json()

        for category in categories:
            results.append(category.get("id"))

        logging.info(f"Category IDs: {results}")
        return results

    def _clean_db(self):
        """
        This function will clean the DB except for the 3 original entries
        :return: None
        """
        def _delete_posts():
            # Remove all orphan posts
            delete_posts = []
            kwargs = {"page": 1,
                      "per_page": 50}
            response = self.get_posts(**kwargs)
            _posts = response.json()
            pages = _posts.get("pages")

            for page in range(0, pages):
                kwargs = {"page": page,
                          "per_page": 50}
                response = self.get_posts(**kwargs)
                _posts = response.json()

                # get IDs to delete
                posts = _posts.get("items")
                for post in posts:
                    if post.get("category_id") is None:
                        delete_posts.append(post.get("id"))

            pool = ThreadPool(processes=5)
            delete_posts = list(set(delete_posts))  # only unique ID values
            for delete in delete_posts:
                pool.apply_async(self.delete_post, args=[delete])
                time.sleep(1.0)  # delay to prevent issues with deleting multiple posts

            # get IDs to delete
            posts = _posts.get("items")
            if len(posts) > 5:
                return True
            return False

        # Remove Categories except for original 3
        logging.info("\n***** DB Cleanup Started *****")
        keep_ids = [1, 2, 3]
        ids = self._get_category_ids()
        delete_ids = set(ids) - set(keep_ids)

        for id in delete_ids:
            self.delete_category(id)

        posts = True
        while posts:
            posts = _delete_posts()
        logging.info("***** DB Cleanup Finished *****\n")

    def _verify_category(self, id=None, name=None):
        """
        Check the id and name of a category
        :param id: <int> : id of category
        :param name: <string> : name of category
        :return: <bool> : True if category id/name matches the expected values
        """
        result = True
        response = self.get_category(id=id)
        category = response.json()

        if id is not None:
            if category.get("id") != id:
                logging.warning(f"ID incorrect, got '{category.get('id')}' but expected '{id}'")
                result = False
            else:
                logging.info(f"ID '{category.get('id')}' as expected")

        if name is not None:
            if category.get("name") != name:
                logging.warning(f"Name incorrect, got '{category.get('name')}' but expected '{name}'")
                result = False
            else:
                logging.info(f"Name '{category.get('name')}' as expected")

        return result

    def _verify_posts(self, expected, page=1, per_page=10):
        """
        This will verify the list of posts that are returned from the blog
        :param expected: <dict> : values you wish to verify (items/page/pages/total)
        :param page: <int> : page number to verify
        :param per_page: <int> : max posts per page
        :return: <bool>
        """
        result = True

        kwargs = {"page": page,
                  "per_page": per_page}
        response = self.get_posts(**kwargs)
        posts = response.json()

        if "items" in expected.keys():
            if expected.get("items") != len(posts.get("items")):
                result = False
                logging.warning(f'Number of Posts on page {len(posts["items"])} but expected {expected.get("items")}')
            else:
                logging.info(f'Number of Posts {len(posts["items"])} as expected')

        if "page" in expected.keys():
            if expected.get("page") != posts.get("page"):
                result = False
                logging.warning(f'Current Page {posts.get("page")} but expected {expected.get("page")}')
            else:
                logging.info(f'Current Page {posts.get("page")} as expected')

        if "pages" in expected.keys():
            if expected.get("pages") != posts.get("pages"):
                result = False
                logging.warning(f'Total Pages {posts.get("pages")} but expected {expected.get("pages")}')
            else:
                logging.info(f'Total pages {posts.get("pages")} as expected')

        if "total" in expected.keys():
            if expected.get("total") != posts.get("total"):
                result = False
                logging.warning(f'Total Posts {posts.get("total")} but expected {expected.get("total")}')
            else:
                logging.info(f'Total Posts {posts.get("total")} as expected')

        if "errors" in expected.keys():
            if expected.get("errors") != posts.get("errors"):
                result = False
                logging.warning(f'Error: {posts.get("errors")} but expected {expected.get("errors")}')
            else:
                logging.info(f'Error {posts.get("errors")} as expected')

        if "message" in expected.keys():
            if expected.get("message") != posts.get("message"):
                result = False
                logging.warning(f'Message: {posts.get("message")} but expected {expected.get("message")}')
            else:
                logging.info(f'Message {posts.get("message")} as expected')

        return result

    def _verify_post(self, expected, id, exclude_id=False):
        """
        This will check the value of a given post id
        :param expected: <dict> : values you wish to verify
        :param id: <int> : id of post to verify
        :param exclude_id: <bool> : if True do not verify the id of post, to get past know bug
        :return: <bool>
        """
        result = True
        response = self.get_post(id=id)
        post = response.json()

        if "title" in expected.keys():
            if expected.get("title") != post.get("title"):
                logging.warning(f"Title incorrect, got '{post.get('title')}' but expected '{expected.get('title')}'")
                result = False
            else:
                logging.info(f"Title '{post.get('title')}' as expected")

        if "body" in expected.keys():
            if expected.get("body") != post.get("body"):
                logging.warning(f"Body incorrect, got '{post.get('body')}' but expected '{expected.get('body')}'")
                result = False
            else:
                logging.info(f"Body '{post.get('body')}' as expected")

        if "category" in expected.keys():
            if expected.get("category") != post.get("category"):
                logging.warning(f"Category incorrect, got '{post.get('category')}' but expected '{expected.get('category')}'")
                result = False
            else:
                logging.info(f"Category '{post.get('category')}' as expected")

        if "category_id" in expected.keys():
            if expected.get("category_id") != post.get("category_id"):
                logging.warning(
                    f"category_id incorrect, got '{post.get('category_id')}' but expected '{expected.get('category_id')}'")
                result = False
            else:
                logging.info(f"Category_id '{post.get('category_id')}' as expected")

        if not exclude_id:
            if "id" in expected.keys():
                if expected.get("id") != post.get("id"):
                    logging.warning(f"id incorrect, got '{post.get('id')}' but expected '{expected.get('id')}'")
                    result = False
                else:
                    logging.info(f"id '{post.get('id')}' as expected")

        return result

    def get_categories(self):
        """
        GET /blog/categories/ - Returns list of blog categories
        :return: <Response>
        """
        logging.info(f"Get Categories: GET {self.categories}")
        response = requests.request("Get", self.categories, headers=self.headers)
        return response

    def create_category(self, name, id=None):
        """
        POST /blog/categories/ - Creates a new blog category
        :param name: <string> : name of the new category
        :param id: <int> : id for new category
        :return: <Response>
        """
        data = {"id": id,
                "name":name}
        json_data = self._json_data(**data)

        logging.info(f"Create Category: POST {self.categories}")
        response = requests.request("Post", self.categories, headers=self.headers, data=json_data)
        return response

    def delete_category(self, id):
        """
        DELETE /blog/categories/{id} - Deletes blog category
        :param: id: <int> : id of category to delete
        :return: <Response>
        """
        url = f"{self.categories}{id}"

        logging.info(f"Delete Category {id}: DELETE {url}")
        response = requests.request("Delete", url, headers=self.headers)
        return response

    def get_category(self, id):
        """
        GET /blog/categories/{id} - Returns a category with a list of posts
        :param: id: <int> : id of category to get post from
        :return: <Response>
        """
        url = f"{self.categories}{id}"

        logging.info(f"Get Category {id}: GET {url}")
        response = requests.request("Get", url, headers=self.headers)
        return response

    def update_category(self, id, name=None):
        """
        PUT /blog/categories/{id} - Updates a blog category
        :param: id: <int> : id of category to get post from
        :param: name: <string> : New name of category
        :return: <Response>
        """
        url = f"{self.categories}{id}"
        data = {"id": id,
                "name": name}
        json_data = self._json_data(**data)

        logging.info(f"Update Category {id}: PUT {url}")
        response = requests.request("Put", url, headers=self.headers, data=json_data)
        return response

    def get_posts(self, page=1, b=True, per_page=10):
        """
        # GET /blog/posts/ - Returns list of blog posts
        :param page: <int> : page number of posts to return
        :param b: <bool> : ????
        :param per_page: <int> : posts to return per page
        :return: <Response>
        """
        data = {"page": page,
                "bool": b,
                "per_page":per_page}
        json_data = self._json_data(**data)

        logging.info(f"Get Posts: GET {self.posts}")
        response = requests.request("Get", self.posts, headers=self.headers, data=json_data)
        return response

    def create_post(self, title, body, category_id=None):
        """
        POST /blog/posts/ - Creates a new blog post
        :param title: <string> : title of the blog post
        :param body: <string> : body of blog post
        :param category_id: <int> : category for post (documentation states: optional)
        return response
        """
        data = {"title": title,
                "body": body,
                "category_id": category_id,
                }

        json_data = self._json_data(**data)

        logging.info(f"Create Post {id}: POST {self.posts}")
        response = requests.request("Post", self.posts, headers=self.headers, data=json_data)
        return response

    def delete_post(self, id):
        """
        DELETE /blog/posts/{id} - Deletes blog post
        :param id: <int> : post id
        return response
        """
        url = f"{self.posts}{id}"
        logging.info(f"Delete Post {id}: DELETE {url}")
        response = requests.request("Delete", url, headers=self.headers)
        return response

    def get_post(self, id):
        """
        GET /blog/posts/{id} - Returns a blog post
        :param id: <int> : post id
        return response
        """
        url = f"{self.posts}{id}"

        logging.info(f"Delete Post {id}: GET {url}")
        response = requests.request("Get", url, headers=self.headers)
        return response

    def update_post(self, id, title, body, category=None, category_id=None, pub_date=None):
        """
        PUT /blog/posts/{id} - Updates a blog post
        :param id: <int> : post id
        :param title: <string> : title of the blog post
        :param body: <string> : body of blog post
        :param category: <string> : title of category
        :param category_id: <int> : id of category post is associated with
        :param pub_date: <datetime> : time post was created
        return response
        """
        url = f"{self.posts}{id}"

        data = {
            "body": body,
            "category": category,
            "category_id": category_id,
            "id": id,
            "pub_date": pub_date,
            "title": title
        }

        logging.info(f"Delete Post {id}: PUT {url}")
        json_data = self._json_data(**data)
        response = requests.request("Put", url, headers=self.headers, data=json_data)
        return response

    def get_archive(self, page, b, per_page, year, month=None, day=None):
        """
        GET /blog/posts/archive/{year}/{month}/{day} - Returns list of blog posts from a specified year
        combined function to allow searching for posts by date
        :param page: <int> : page number of posts to return
        :param b: <bool> : ????
        :param per_page: <int> : posts to return per page
        :param year: <int> : year of posts to return
        :param month: <int> : month of posts to return
        :param day: <int> : day of posts to return
        return response
        """
        url = f"{self.archive}{year}/"
        if month is not None:
            url = f"{url}{month}/"
            if day is not None:
                url = f"{url}{day}/"

        data = {"page": page,
                "bool": b,
                "per_page": per_page}
        json_data = self._json_data(**data)

        logging.info(f"Get Archive: GET {url}")
        response = requests.request("Get", url, headers=self.headers, data=json_data)
        return response

