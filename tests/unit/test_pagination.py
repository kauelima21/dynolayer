import pytest
from dynolayer.utils import Collection


class TestPaginationMetadata:
    """Test pagination metadata (last_evaluated_key and get_count)"""

    def test_last_evaluated_key_is_set_with_limit(self, get_user, create_table, aws_mock, save_records):
        """Test that last_evaluated_key is set when results are limited"""
        query = get_user().all().limit(5)
        result = query.get()

        assert isinstance(result, Collection)
        assert query.last_evaluated_key() is not None
        assert isinstance(query.last_evaluated_key(), dict)

    def test_last_evaluated_key_is_none_when_all_returned(self, get_user, create_table, aws_mock, save_records):
        """Test that last_evaluated_key is None when all results are returned"""
        query = get_user().all()
        result = query.get(return_all=True)

        assert isinstance(result, Collection)
        assert query.last_evaluated_key() is None

    def test_get_count_reflects_returned_items(self, get_user, create_table, aws_mock, save_records):
        """Test that get_count reflects the number of items returned in the current page"""
        query = get_user().all().limit(10)
        result = query.get()

        assert isinstance(result, Collection)
        assert query.get_count() == 10
        assert result.count() == 10

    def test_get_count_with_return_all(self, get_user, create_table, aws_mock, save_records):
        """Test that get_count reflects all items when return_all=True"""
        query = get_user().all()
        result = query.get(return_all=True)

        assert isinstance(result, Collection)
        assert query.get_count() == 20
        assert result.count() == 20


class TestOffsetMethod:
    """Test the offset() method for manual pagination"""

    def test_offset_returns_next_page(self, get_user, create_table, aws_mock, save_records):
        """Test that offset() returns the next page of results"""
        # Get first page
        query1 = get_user().all().limit(5)
        first_page = query1.get()
        first_page_ids = first_page.pluck("id")
        last_key = query1.last_evaluated_key()

        assert last_key is not None
        assert len(first_page_ids) == 5

        # Get second page using offset
        query2 = get_user().all().limit(5).offset(last_key)
        second_page = query2.get()
        second_page_ids = second_page.pluck("id")

        assert len(second_page_ids) == 5
        # Ensure pages don't overlap
        assert not any(item_id in first_page_ids for item_id in second_page_ids)

    def test_offset_with_where_clause(self, get_user, create_table, aws_mock, save_records):
        """Test that offset() works with where clauses"""
        # First, get users with a specific role
        user1 = get_user()
        first_page = (
            user1.where("role", "admin")
            .index("role-index")
            .limit(2)
            .get()
        )

        if user1.last_evaluated_key() is not None:
            # Get second page using offset
            user2 = get_user()
            second_page = (
                user2.where("role", "admin")
                .index("role-index")
                .limit(2)
                .offset(user1.last_evaluated_key())
                .get()
            )

            assert isinstance(second_page, Collection)
            # Verify all results have the correct role
            for item in second_page:
                assert item.role == "admin"


class TestCountMethod:
    """Test the count() method"""

    def test_count_returns_total_count(self, get_user, create_table, aws_mock, save_records):
        """Test that count() returns the total count of all matching records"""
        user = get_user()

        total = user.all().count()

        assert total == 20

    def test_count_with_where_clause(self, get_user, create_table, aws_mock, save_records):
        """Test that count() works with where clauses"""
        user = get_user()

        # Count users with a specific role
        admin_count = (
            user.where("role", "admin")
            .index("role-index")
            .count()
        )

        assert isinstance(admin_count, int)
        assert admin_count >= 0

    def test_count_with_force_scan(self, get_user, create_table, aws_mock, save_records):
        """Test that count() works with force_scan"""
        user = get_user()

        count = (
            user.where("stars", ">", 3)
            .force_scan()
            .count()
        )

        assert isinstance(count, int)
        assert count >= 0


class TestManualPaginationWorkflow:
    """Test the complete manual pagination workflow as shown in documentation"""

    def test_manual_pagination_api_pattern(self, get_user, create_table, aws_mock, save_records):
        """Test the pagination pattern from the documentation"""
        limit = 5

        # Get total count
        total_count = get_user().all().count()
        assert total_count == 20

        # Build query
        query = get_user().all().limit(limit)

        # Execute query
        results = query.fetch()

        # Get result count and next page token
        results_count = query.get_count()
        next_key = query.last_evaluated_key()

        # Verify pagination data
        assert isinstance(results, Collection)
        assert results_count == limit
        assert next_key is not None

        # Build API-like response
        response = {
            'total_count': total_count,
            'results': results.to_list(),
            'results_count': results_count,
            'last_evaluated_key': next_key
        }

        assert response['total_count'] == 20
        assert len(response['results']) == 5
        assert response['results_count'] == 5
        assert response['last_evaluated_key'] is not None

    def test_paginate_through_all_records(self, get_user, create_table, aws_mock, save_records):
        """Test paginating through all records manually"""
        limit = 7
        all_ids = []
        last_evaluated_key = None

        # Paginate through all records
        while True:
            query = get_user().all().limit(limit)

            if last_evaluated_key:
                query = query.offset(last_evaluated_key)

            results = query.fetch()
            all_ids.extend(results.pluck("id"))

            last_evaluated_key = query.last_evaluated_key()

            # Break if no more pages
            if last_evaluated_key is None:
                break

        # Verify we got all 20 records
        assert len(all_ids) == 20
        # Verify no duplicates
        assert len(set(all_ids)) == 20


class TestAutomaticPagination:
    """Test automatic pagination with return_all=True"""

    def test_automatic_pagination_with_all(self, get_user, create_table, aws_mock, save_records):
        """Test automatic pagination using all().get(return_all=True)"""
        all_users = get_user().all().get(return_all=True)

        assert isinstance(all_users, Collection)
        assert all_users.count() == 20

    def test_automatic_pagination_with_where(self, get_user, create_table, aws_mock, save_records):
        """Test automatic pagination with where clause"""
        # Add more records to ensure pagination
        user_model = get_user()
        for i in range(10):
            user_model.create({
                "id": 100 + i,
                "role": "admin",
                "first_name": f"Admin{i}",
                "email": f"admin{i}@mail.com",
            })

        # Get all admin users
        all_admins = (
            get_user()
            .where("role", "admin")
            .index("role-index")
            .get(return_all=True)
        )

        assert isinstance(all_admins, Collection)
        # Verify all have admin role
        for user in all_admins:
            assert user.role == "admin"


if __name__ == "__main__":
    pytest.main()
