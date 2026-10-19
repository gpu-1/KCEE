#include "dictionary.H"
#include "IStringStream.H"
#include "OStringStream.H"
#include "OSHA1stream.H"
#include <iostream>
int main()
{
    Foam::OSHA1stream stream;
    stream << 'a' << Foam::word("bc");
    if (stream.digest().str() != "a9993e364706816aba3e25717850c26c9cd0d89d") return 1;
    Foam::IStringStream input("type forces; rhoInf 1; patches (bracket);");
    Foam::dictionary dict(input);
    Foam::OStringStream serialized;
    for (const Foam::entry& entry : dict) serialized << entry;
    Foam::SHA1 expected(serialized.str());
    if (dict.digest() != expected.digest()) return 2;
    std::cout << "SHA1 mixed character/string and dictionary serialization verified\n";
    return 0;
}
