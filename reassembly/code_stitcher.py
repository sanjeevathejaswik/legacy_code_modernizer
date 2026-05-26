"""
CodeStitcher
============
Takes the LLM-generated project config + converted modules/tests and writes a
complete, compilable Maven project tree to output/assembled/.

Output layout
─────────────
output/assembled/
├── pom.xml
├── Dockerfile
├── src/
│   ├── main/
│   │   ├── java/<group_path>/<module>.java  (one per converted module)
│   │   └── resources/
│   │       └── application.yml
│   └── test/
│       └── java/<group_path>/<test>.java    (one per test suite)
├── assembly_manifest.json
└── dependency_graph.json
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import config


# ── Manifest ──────────────────────────────────────────────────────────────────

@dataclass
class AssemblyManifest:
    project_name:       str
    group_id:           str
    artifact_id:        str
    project_root:       str
    total_files:        int             = 0
    source_files:       List[str]       = field(default_factory=list)
    test_files:         List[str]       = field(default_factory=list)
    config_files:       List[str]       = field(default_factory=list)
    warnings:           List[str]       = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "project_name":  self.project_name,
            "group_id":      self.group_id,
            "artifact_id":   self.artifact_id,
            "project_root":  self.project_root,
            "total_files":   self.total_files,
            "source_files":  self.source_files,
            "test_files":    self.test_files,
            "config_files":  self.config_files,
            "warnings":      self.warnings,
        }


# ── Templates ─────────────────────────────────────────────────────────────────

def _pom_xml(cfg: Dict) -> str:
    group_id    = cfg.get("group_id",    "com.bank")
    artifact_id = cfg.get("artifact_id", "legacy-modernised")
    version     = cfg.get("version",     "1.0.0-SNAPSHOT")
    sb_version  = cfg.get("spring_boot_version", "3.2.0")

    extra_deps = ""
    for dep in cfg.get("dependencies", []):
        gid = dep.get("groupId",    "")
        aid = dep.get("artifactId", "")
        ver = dep.get("version",    "")
        scope = dep.get("scope",    "")
        if gid and aid:
            ver_tag   = f"\n            <version>{ver}</version>" if ver else ""
            scope_tag = f"\n            <scope>{scope}</scope>"  if scope else ""
            extra_deps += f"""
        <dependency>
            <groupId>{gid}</groupId>
            <artifactId>{aid}</artifactId>{ver_tag}{scope_tag}
        </dependency>"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>{sb_version}</version>
        <relativePath/>
    </parent>

    <groupId>{group_id}</groupId>
    <artifactId>{artifact_id}</artifactId>
    <version>{version}</version>
    <packaging>jar</packaging>

    <properties>
        <java.version>17</java.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springdoc</groupId>
            <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
            <version>2.3.0</version>
        </dependency>
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
        </dependency>
        <dependency>
            <groupId>com.h2database</groupId>
            <artifactId>h2</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.mockito</groupId>
            <artifactId>mockito-core</artifactId>
            <scope>test</scope>
        </dependency>{extra_deps}
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
                <configuration>
                    <excludes>
                        <exclude>
                            <groupId>org.projectlombok</groupId>
                            <artifactId>lombok</artifactId>
                        </exclude>
                    </excludes>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
"""


def _dockerfile(artifact_id: str, version: str) -> str:
    jar = f"{artifact_id}-{version}.jar"
    return f"""# ── Build stage ─────────────────────────────────────────────────────────────
FROM eclipse-temurin:17-jdk-alpine AS builder
WORKDIR /app
COPY . .
RUN ./mvnw -q package -DskipTests

# ── Runtime stage ────────────────────────────────────────────────────────────
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=builder /app/target/{jar} app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
"""


def _default_application_yml(group_id: str, artifact_id: str) -> str:
    return f"""spring:
  application:
    name: {artifact_id}
  datasource:
    url: jdbc:h2:mem:testdb
    driver-class-name: org.h2.Driver
    username: sa
    password:
  jpa:
    hibernate:
      ddl-auto: create-drop
    show-sql: false
  h2:
    console:
      enabled: true

server:
  port: 8080

springdoc:
  api-docs:
    path: /api-docs
  swagger-ui:
    path: /swagger-ui.html

logging:
  level:
    root: INFO
    {group_id}: DEBUG
"""


# ── Stitcher ──────────────────────────────────────────────────────────────────

class CodeStitcher:
    """
    Writes the full Maven project tree given:
      • project_config  — dict from the Joiner LLM call
      • converted_modules — list of ConvertedModule dicts
      • test_suites       — list of TestSuite dicts
      • dep_graph_dict    — DependencyGraph.to_dict()
    """

    def __init__(self, output_root: str = "") -> None:
        self._root = Path(output_root or f"{config.OUTPUT_DIR}/assembled")

    # ── Public API ────────────────────────────────────────────────────────────

    def stitch(
        self,
        project_config:    Dict,
        converted_modules: List[Dict],
        test_suites:       List[Dict],
        dep_graph_dict:    Dict,
    ) -> AssemblyManifest:
        group_id    = project_config.get("group_id",    "com.bank.legacy")
        artifact_id = project_config.get("artifact_id", "modernised-service")
        version     = project_config.get("version",     "1.0.0-SNAPSHOT")
        project_name = project_config.get("project_name", artifact_id)

        manifest = AssemblyManifest(
            project_name=project_name,
            group_id=group_id,
            artifact_id=artifact_id,
            project_root=str(self._root),
        )

        self._root.mkdir(parents=True, exist_ok=True)

        # Root config files
        self._write("pom.xml",    _pom_xml(project_config),          manifest, "config")
        self._write("Dockerfile", _dockerfile(artifact_id, version), manifest, "config")

        # application.yml — prefer LLM version, fall back to template
        app_yml = (
            project_config.get("application_yml")
            or _default_application_yml(group_id, artifact_id)
        )
        yml_path = "src/main/resources/application.yml"
        self._write(yml_path, app_yml, manifest, "config")

        # Main @SpringBootApplication class
        main_code = project_config.get("main_class_code") or self._default_main(group_id)
        main_path = self._java_path("main", group_id, f"{self._pascal(artifact_id)}Application")
        self._write(main_path, main_code, manifest, "source")

        # Source modules
        for mod in converted_modules:
            code = mod.get("java_code", "")
            if not code:
                manifest.warnings.append(f"No java_code for module {mod.get('name')}")
                continue
            pkg  = mod.get("package", group_id)
            name = mod.get("name", "Unknown")
            path = self._java_path("main", pkg, name)
            self._write(path, code, manifest, "source")

        # Test suites — infer package from module lookup
        mod_pkg_map = {m.get("name"): m.get("package", group_id) for m in converted_modules}
        for suite in test_suites:
            code = suite.get("test_code", "")
            if not code:
                continue
            module_name = suite.get("module_name", "")
            pkg = mod_pkg_map.get(module_name, group_id)
            test_class = suite.get("test_class_name", f"{module_name}Test")
            path = self._java_path("test", pkg, test_class)
            self._write(path, code, manifest, "test")

        # Persist dependency graph
        dg_path = self._root / "dependency_graph.json"
        dg_path.write_text(json.dumps(dep_graph_dict, indent=2), encoding="utf-8")

        # Persist assembly manifest
        manifest.total_files = (
            len(manifest.source_files)
            + len(manifest.test_files)
            + len(manifest.config_files)
        )
        mf_path = self._root / "assembly_manifest.json"
        mf_path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")

        return manifest

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _java_path(self, src_or_test: str, package: str, class_name: str) -> str:
        pkg_path = package.replace(".", "/")
        return f"src/{src_or_test}/java/{pkg_path}/{class_name}.java"

    def _write(self, relative: str, content: str, manifest: AssemblyManifest, kind: str) -> None:
        full = self._root / relative
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        if kind == "source":
            manifest.source_files.append(relative)
        elif kind == "test":
            manifest.test_files.append(relative)
        else:
            manifest.config_files.append(relative)

    @staticmethod
    def _pascal(kebab: str) -> str:
        return "".join(w.capitalize() for w in kebab.replace("-", "_").split("_"))

    @staticmethod
    def _default_main(group_id: str) -> str:
        return f"""package {group_id};

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class Application {{

    public static void main(String[] args) {{
        SpringApplication.run(Application.class, args);
    }}
}}
"""
