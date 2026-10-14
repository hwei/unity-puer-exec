using System.Runtime.CompilerServices;

// The package's EditMode test assembly (Tests/EditMode/UnityPuerExec.EditMode.Tests.asmdef)
// exercises the internal server-side job state and response builders directly. Granting
// it access here keeps that coverage possible without widening the package's public API.
// The test assembly is Editor-only and gated by UNITY_INCLUDE_TESTS, so this changes
// nothing for a player build or a package consumer.
[assembly: InternalsVisibleTo("UnityPuerExec.EditMode.Tests")]
