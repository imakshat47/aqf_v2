from .field_mapper import FieldMapper


class JsonQueryExecutor:

    def execute(
        self,
        records,
        conditions,
        return_fields
    ):

        matches = []

        for record in records:

            if self._matches(record, conditions):

                row = {}

                for field in return_fields:

                    values = FieldMapper.extract(
                        record,
                        field
                    )

                    row[field] = values[0] if values else None

                matches.append(row)

        return matches

    def _matches(
        self,
        record,
        conditions
    ):

        for cond in conditions:

            values = FieldMapper.extract(
                record,
                cond.field_path
            )

            if not values:
                return False

            if not self._evaluate(
                values[0],
                cond.operator,
                cond.value
            ):
                return False

        return True
    
    def _coerce_numeric(self, value):
        try:
            return float(value)
        except Exception:
            return None
    
    def _evaluate(
        self,
        actual,
        operator,
        expected
    ):

        try:

            if operator == "=":
                return str(actual) == str(expected)

            if operator == "!=":
                return str(actual) != str(expected)

            actual_num = self._coerce_numeric(actual)
            expected_num = self._coerce_numeric(expected)

            if operator == ">":
            
                if actual_num is None or expected_num is None:
                    return False

                return actual_num > expected_num

            if operator == "<":
            
                if actual_num is None or expected_num is None:
                    return False

                return actual_num < expected_num

            if operator == ">=":
            
                if actual_num is None or expected_num is None:
                    return False

                return actual_num >= expected_num

            if operator == "<=":
            
                if actual_num is None or expected_num is None:
                    return False

                return actual_num <= expected_num

            if operator == "contains":
                return str(expected).lower() in str(actual).lower()

        except Exception:
            return False

        return False