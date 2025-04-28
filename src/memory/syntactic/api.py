import tree_sitter


class API:
    def __init__(
        self,
        api_id: int,
        api_name: str,
        api_para_num: int,
    ) -> None:
        """
        Record basic facts of the API.
        Here, API indicates the library function
        """
        self.api_id = api_id
        self.api_name = api_name
        self.api_para_num = api_para_num

    def __str__(self) -> str:
        return f"API(api_id={self.api_id}, api_name='{self.api_name}', api_para_num={self.api_para_num})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, API):
            return NotImplemented
        return (
            self.api_name == other.api_name and self.api_para_num == other.api_para_num
        )

    def __hash__(self) -> int:
        return hash((self.api_name, self.api_para_num))
