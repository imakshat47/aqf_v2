class FieldMapper:

    @staticmethod
    def extract(record, field_path):

        target = field_path.split("/")[-1].strip().lower()

        results = []

        def walk(obj):

            if isinstance(obj, dict):

                name = obj.get("name")

                if isinstance(name, dict):

                    label = str(
                        name.get("value", "")
                    ).lower()

                    if label == target:

                        value = obj.get("value")

                        if isinstance(value, dict):
                        
                            #
                            # DV_COUNT / DV_QUANTITY
                            #
                            if "magnitude" in value:
                            
                                results.append(
                                    value.get("magnitude")
                                )
                        
                            #
                            # DV_TEXT
                            # DV_CODED_TEXT
                            # DV_DATE
                            # DV_DATE_TIME
                            #
                            elif "value" in value:
                            
                                results.append(
                                    value.get("value")
                                )
                        
                            #
                            # fallback
                            #
                            else:
                            
                                results.append(str(value))
                        
                        else:
                        
                            results.append(value)

                for v in obj.values():
                    walk(v)

            elif isinstance(obj, list):

                for x in obj:
                    walk(x)

        walk(record)

        return results