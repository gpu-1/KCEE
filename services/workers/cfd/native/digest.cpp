// OpenFOAM dictionary hashing compatibility fix, scoped to native postprocessing.
// Based on OpenFOAM 1912 dictionary::digest (GPL-3.0-or-later) and the
// overflow fix described by OpenFOAM Foundation commit b0c15bebd37142f3.
// No digest checks are bypassed: every serialized entry is hashed normally.
#include "dictionary.H"
#include "OSHA1stream.H"
Foam::SHA1Digest Foam::dictionary::digest() const
{
    OSHA1stream os;
    for (const entry& e : *this) { os << e; }
    return os.digest();
}
