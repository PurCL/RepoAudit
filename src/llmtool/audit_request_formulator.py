from os import path
import json
import time
from typing import List, Set, Optional, Dict
from llmtool.LLM_utils import *
from llmtool.LLM_tool import *
from memory.syntactic.function import *
from memory.syntactic.value import *
from memory.syntactic.api import *

BASE_PATH = Path(__file__).resolve().parent.parent


class AuditRequestFormulatorInput(LLMToolInput):
    def __init__(self, user_prompt_str: str) -> None:
        """
        :param user_prompt_str: the user prompt string
        """
        self.user_prompt_str = user_prompt_str
        return

    def __hash__(self) -> int:
        return hash(self.user_prompt_str)


class AuditRequestFormulatorOutput(LLMToolOutput):
    class Scope(ABC):
        def __init__(self, type: str) -> None:
            self.type = type
            return

    class FileScope(Scope):
        def __init__(self, file_paths: List[str]) -> None:
            super().__init__("FileLevel")
            self.file_paths = file_paths
            return

        def __str__(self):
            return f"Files: {self.file_paths}"

    class DirectoryScope(Scope):
        def __init__(self, directory_paths: List[str]) -> None:
            super().__init__("DirectoryLevel")
            self.directory_paths = directory_paths
            return

        def __str__(self):
            return f"Directories: {self.directory_paths}"

    class RepoScope(Scope):
        def __init__(self) -> None:
            super().__init__("RepoLevel")
            return

    def __init__(self, bug_type: str, scope: Scope) -> None:
        self.bug_type = bug_type
        self.scope = scope
        return

    def __str__(self):
        if (
            isinstance(self.scope, AuditRequestFormulatorOutput.FileScope)
            or isinstance(self.scope, AuditRequestFormulatorOutput.DirectoryScope)
            or isinstance(self.scope, AuditRequestFormulatorOutput.RepoScope)
        ):
            return str(self.bug_type) + str(self.scope)
        else:
            raise RAValueError("Unknown scope type")


class AuditRequestFormulator(LLMTool):
    def __init__(
        self,
        model_name: str,
        temperature: float,
        language: str,
        max_query_num: int,
        logger: Logger,
    ) -> None:
        super().__init__(model_name, temperature, language, max_query_num, logger)
        self.prompt_file = f"{BASE_PATH}/prompt/audit_request_formulator.json"
        return

    def _get_prompt(self, audit_request_formulator_input: LLMToolInput) -> str:
        if not isinstance(audit_request_formulator_input, AuditRequestFormulatorInput):
            raise RAValueError(
                f"Input type {type(audit_request_formulator_input)} is not supported."
            )

        with open(self.prompt_file, "r") as f:
            prompt_template_dict = json.load(f)

        prompt = prompt_template_dict["task"]
        prompt += "\n" + "".join(prompt_template_dict["meta_prompts"])
        prompt = prompt.replace(
            "<ANSWER>", "\n".join(prompt_template_dict["answer_format"])
        )
        prompt = prompt.replace(
            "<DESCRIPTION>", audit_request_formulator_input.user_prompt_str
        )
        return prompt

    def _parse_response(
        self,
        response: str,
        audit_request_formulator_input: Optional[LLMToolInput] = None,
    ) -> Optional[LLMToolOutput]:
        """
        Parse the response from the model.
        :param response: the response from the model
        :param audit_request_formulator_input: the audit_request_formulator_input of the tool
        :return: the output of the tool
        """
        if not isinstance(audit_request_formulator_input, AuditRequestFormulatorInput):
            raise RAValueError(
                f"Input type {type(audit_request_formulator_input)} is not supported."
            )

        pattern = r"- Bug Type:\s*(.*?)[,;]?\s*\n- Scope Type:\s*(.*?)[,;]?\s*\n- Scope:\s*(.*?)[,;]?\s*$"
        match = re.search(pattern, response, re.MULTILINE)
        if match:
            bug_type = match.group(1).strip()
            scope_type = match.group(2).strip()
            scope_str = match.group(3).strip()
            scope_list = [s.strip() for s in scope_str.split(",")]

            if bug_type not in {"NPD", "MLK", "UAF", "BOF"}:
                return None

            scope: AuditRequestFormulatorOutput.Scope
            if scope_type == "FileLevel":
                scope = AuditRequestFormulatorOutput.FileScope(scope_list)
            elif scope_type == "DirectoryLevel":
                scope = AuditRequestFormulatorOutput.DirectoryScope(scope_list)
            elif scope_type == "RepoLevel":
                scope = AuditRequestFormulatorOutput.RepoScope()
            else:
                return None

            return AuditRequestFormulatorOutput(bug_type, scope)
        else:
            print("No match found")
            return None
