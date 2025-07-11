"""
CLI Interface for Pyramid MCP Stdio Transport

Simple CLI that loads Pyramid applications from INI files and provides
stdio transport for MCP protocol communication.
"""

import json
import logging
import sys
import time
from datetime import datetime
from typing import Any

import click
from pyramid.paster import bootstrap

logger = logging.getLogger(__name__)


@click.command()
@click.option("--ini", type=click.Path(exists=True), help="Path to Pyramid INI file")
@click.option(
    "--app", help="Python module:function to load app (e.g., simple_app:create_app)"
)
@click.option("--debug", is_flag=True, help="Enable debug logging")
def pstdio(ini: str, app: str, debug: bool) -> None:
    """Run Pyramid MCP server with stdio transport.

    Load a Pyramid application and run an MCP server that communicates
    via stdin/stdout for Claude Desktop integration.

    Examples:

        # Load from INI file
        pstdio --ini development.ini

        # Load from Python module
        pstdio --app simple_app:create_app

        # With debug logging
        pstdio --app simple_app:create_app --debug
    """

    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
            stream=sys.stderr,
        )
        click.echo("🐛 Debug mode enabled", err=True)
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)-8s %(message)s",
            stream=sys.stderr,
        )

    if not ini and not app:
        raise click.ClickException("Must specify either --ini or --app")

    if ini and app:
        raise click.ClickException("Cannot specify both --ini and --app")

    try:
        if ini:
            # Load Pyramid application from INI file using Pyramid's bootstrap
            click.echo(f"📄 Loading Pyramid app from INI: {ini}", err=True)
            env = bootstrap(ini)
            app_instance = env["app"]
        else:
            # Load Pyramid application from Python module
            click.echo(f"🐍 Loading Pyramid app from module: {app}", err=True)
            module_name, func_name = app.split(":")

            import importlib

            module = importlib.import_module(module_name)
            create_app_func = getattr(module, func_name)
            app_instance = create_app_func()

        if debug:
            click.echo(f"✅ App loaded successfully: {type(app_instance)}", err=True)

        # Get the PyramidMCP instance from app registry
        if not hasattr(app_instance.registry, "pyramid_mcp"):
            raise click.ClickException(
                "No PyramidMCP instance found. "
                "Make sure your app includes pyramid_mcp: "
                "config.include('pyramid_mcp')"
            )

        pyramid_mcp = app_instance.registry.pyramid_mcp

        # Ensure tools are discovered
        if not pyramid_mcp._tools_discovered:
            pyramid_mcp.discover_tools()

        protocol_handler = pyramid_mcp.protocol_handler

        # Start stdio server
        click.echo("🔐 Pyramid MCP Stdio Server Starting...", err=True)
        click.echo(
            f"✓ Server: {protocol_handler.server_name} "
            + f"v{protocol_handler.server_version}",
            err=True,
        )
        click.echo(f"✓ Tools registered: {len(protocol_handler.tools)}", err=True)

        if debug:
            click.echo("📋 Available tools:", err=True)
            for tool_name in protocol_handler.tools:
                click.echo(f"  - {tool_name}", err=True)

        click.echo("🎧 Listening for Claude Desktop requests...", err=True)
        click.echo("=" * 60, err=True)

        # Simple stdio loop for JSON-RPC communication with logging
        request_count = 0
        try:
            while True:
                # Read JSON-RPC request from stdin
                line = sys.stdin.readline().strip()
                if not line:
                    logger.info("📴 No more input - Claude Desktop disconnected")
                    break

                request_count += 1
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

                try:
                    # Parse JSON-RPC request
                    request_data = json.loads(line)

                    # Log the incoming request from Claude
                    method = request_data.get("method", "unknown")
                    request_id = request_data.get("id", "no-id")

                    click.echo(
                        f"📥 [{timestamp}] Request #{request_count} from Claude:",
                        err=True,
                    )
                    click.echo(f"   Method: {method}", err=True)
                    click.echo(f"   ID: {request_id}", err=True)

                    if debug:
                        click.echo(
                            f"   📝 Full request: {json.dumps(request_data, indent=2)}",
                            err=True,
                        )
                    elif "params" in request_data:
                        params = request_data["params"]
                        if isinstance(params, dict):
                            if "name" in params:  # Tool call
                                tool_name = params["name"]
                                args = params.get("arguments", {})
                                click.echo(f"   Tool: {tool_name}", err=True)
                                if args:
                                    click.echo(f"   Args: {json.dumps(args)}", err=True)
                            elif method == "tools/list":
                                click.echo(
                                    "   Action: List all available tools", err=True
                                )
                            else:
                                click.echo(f"   Params: {json.dumps(params)}", err=True)

                    # Handle request using protocol handler
                    # Create a proper request for stdio transport
                    from pyramid.scripting import prepare

                    env = prepare(registry=app_instance.registry)
                    request = env["request"]

                    # Add invoke_subrequest method to the request since it's not
                    # available in the scripting context (normally added by router)
                    def invoke_subrequest(
                        subrequest: Any, use_tweens: bool = False
                    ) -> Any:
                        """Invoke a subrequest through the WSGI application.

                        This replicates what the Pyramid router does internally.
                        """
                        # The router adds registry and invoke_subrequest to subrequests
                        subrequest.registry = app_instance.registry

                        # Add invoke_subrequest recursively to support nested
                        # subrequests
                        subrequest.invoke_subrequest = (
                            lambda sr, ut=False: invoke_subrequest(sr, ut)
                        )

                        # Apply request extensions like the router does
                        from pyramid.request import apply_request_extensions

                        apply_request_extensions(subrequest)

                        # Process the subrequest through the WSGI application
                        # This is the core of what invoke_subrequest does
                        return subrequest.get_response(app_instance)

                    # Add the method to the request
                    request.invoke_subrequest = invoke_subrequest

                    start_time = time.time()
                    response = protocol_handler.handle_message(request_data, request)
                    processing_time = (time.time() - start_time) * 1000

                    # Check if this is a notification that should not receive a response
                    if response is protocol_handler.NO_RESPONSE:
                        # Don't send any response for notifications (JSON-RPC 2.0 spec)
                        click.echo(
                            f"📤 [{timestamp}] No response sent for notification "
                            f"(took {processing_time:.1f}ms)",
                            err=True,
                        )
                        click.echo("─" * 60, err=True)
                        continue

                    # Log the response we're sending back to Claude
                    response_msg = (
                        f"📤 [{timestamp}] Response to Claude "
                        f"(took {processing_time:.1f}ms):"
                    )
                    click.echo(response_msg, err=True)

                    if "error" in response:
                        error = response["error"]
                        click.echo(
                            f"   ❌ Error: {error.get('message', 'Unknown error')}",
                            err=True,
                        )
                        if debug:
                            click.echo(
                                f"   📝 Full error: {json.dumps(error, indent=2)}",
                                err=True,
                            )
                    elif "result" in response:
                        result = response["result"]
                        if method == "tools/list":
                            tools = result.get("tools", [])
                            click.echo(f"   ✅ Listed {len(tools)} tools", err=True)
                        elif method == "tools/call":
                            content = result.get("content", [])
                            if content and len(content) > 0:
                                text_content = content[0].get("text", "")
                                preview = (
                                    text_content[:100] + "..."
                                    if len(text_content) > 100
                                    else text_content
                                )
                                click.echo(f"   ✅ Tool result: {preview}", err=True)
                            else:
                                click.echo("   ✅ Tool executed (no content)", err=True)
                        else:
                            click.echo(
                                f"   ✅ Success: {json.dumps(result)[:100]}...",
                                err=True,
                            )

                    if debug:
                        click.echo(
                            f"   📝 Full response: {json.dumps(response, indent=2)}",
                            err=True,
                        )

                    click.echo("─" * 60, err=True)

                    # Write JSON-RPC response to stdout
                    print(json.dumps(response), flush=True)

                except json.JSONDecodeError as e:
                    error_msg = f"Invalid JSON from Claude: {e}"
                    logger.error(f"❌ {error_msg}")
                    click.echo(f"📥 [{timestamp}] ❌ JSON Parse Error: {e}", err=True)
                    click.echo(f"   Raw input: {line}", err=True)
                    click.echo("─" * 60, err=True)

                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "Parse error"},
                    }
                    print(json.dumps(error_response), flush=True)

                except Exception as e:
                    error_msg = f"Error processing request: {e}"
                    logger.error(f"❌ {error_msg}")
                    click.echo(f"📥 [{timestamp}] ❌ Processing Error: {e}", err=True)
                    if debug:
                        import traceback

                        click.echo(
                            f"   📝 Traceback: {traceback.format_exc()}", err=True
                        )
                    click.echo("─" * 60, err=True)

                    error_response = {
                        "jsonrpc": "2.0",
                        "id": (
                            request_data.get("id")
                            if "request_data" in locals()
                            else None
                        ),
                        "error": {"code": -32603, "message": "Internal error"},
                    }
                    print(json.dumps(error_response), flush=True)

        except KeyboardInterrupt:
            click.echo("\n🛑 Keyboard interrupt received", err=True)
        except BrokenPipeError:
            logger.info("📴 Broken pipe - Claude Desktop disconnected")
        except EOFError:
            logger.info("📴 EOF reached - Claude Desktop disconnected")

        total_time = datetime.now().strftime("%H:%M:%S")
        click.echo("=" * 60, err=True)
        click.echo(f"👋 Shutting down stdio server at {total_time}", err=True)
        click.echo(f"📊 Total requests processed: {request_count}", err=True)

    except Exception as e:
        if debug:
            import traceback

            traceback.print_exc()
        click.echo(f"💥 Fatal error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    pstdio()
